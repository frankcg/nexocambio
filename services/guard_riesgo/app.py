"""
NexoGuard — Agente de Riesgo  (AWS Lambda · Python 3.12 · paso EvaluarRiesgo)

1. Las reglas calculan un semáforo MÍNIMO (rojo si hay discrepancias duras, amarillo si hay
   motivos de revisión o el monto supera el umbral de registro, verde si todo cumple).
2. Groq (modelo de texto, sin memoria) evalúa la operación y redacta la justificación.
   Puede SUBIR el semáforo, nunca bajarlo: el agente escala, no aprueba lo que las reglas no aprueban.
   Sin discrepancias duras solo puede subir hasta amarillo: un rechazo siempre se basa en una regla.
3. Se fija la ruta: rojo → rechazar · amarillo → revision · verde → aprobar.

Salida: {semaforo, ruta, justificacion, motivo_rechazo, alerta_cumplimiento, monto_usd, modelo}
"""
import json
import os

from nexo_common import log
from nexo_groq import chat_json

NIVEL = {"verde": 0, "amarillo": 1, "rojo": 2}
RUTA = {"verde": "aprobar", "amarillo": "revision", "rojo": "rechazar"}
# Equivalencias referenciales para estimar el monto en USD cuando ninguna moneda es USD
USD_POR = {"USD": 1.0, "USDT": 1.0, "USDC": 1.0, "PEN": 1 / 3.4, "EUR": 1.08}

PROMPT = """Eres el analista de riesgo de NexoCambio, una casa de cambio digital peruana (sujeto obligado ante la UIF-Perú).
Evalúa si la operación puede procesarse con el comprobante presentado. Datos:
{datos}

Reglas: el semáforo mínimo calculado por el sistema es "{minimo}". Puedes subirlo (verde < amarillo < rojo)
si ves algo sospechoso en los datos, pero NUNCA bajarlo. No inventes hechos que no estén en los datos.
Responde SOLO con un JSON:
{{"semaforo": "verde"|"amarillo"|"rojo",
  "justificacion": "máximo 3 oraciones en español, citando los hechos evaluados",
  "motivo_rechazo": "si el semáforo es rojo, una oración clara y amable para el cliente; si no, null"}}"""


def monto_usd(op: dict) -> float:
    for moneda, monto in ((op["moneda_origen"], op["monto_origen"]), (op["moneda_destino"], op["monto_destino"])):
        if moneda in ("USD", "USDT", "USDC"):
            return round(float(monto), 2)
    return round(float(op["monto_origen"]) * USD_POR.get(op["moneda_origen"], 0.0), 2)


def semaforo_minimo(ver: dict, alerta: bool) -> str:
    if ver["discrepancias_duras"]:
        return "rojo"
    return "amarillo" if (not ver["todo_cumple"] or alerta) else "verde"


def evaluar(op: dict, ex: dict, ver: dict) -> dict:
    umbral = float(os.environ.get("UMBRAL_USD", "10000"))
    usd = monto_usd(op)
    alerta = usd >= umbral
    minimo = semaforo_minimo(ver, alerta)
    datos = {
        "operacion": {k: op.get(k) for k in ("id_operacion", "modalidad", "moneda_origen", "moneda_destino",
                                             "monto_origen", "monto_destino", "fecha_operacion")},
        "banco_origen_declarado": (op.get("origen") or {}).get("banco"),
        "monto_equivalente_usd": usd, "umbral_registro_uif_usd": umbral,
        "comprobante_leido": {k: ex.get(k) for k in ("es_comprobante", "legible", "banco_origen", "monto", "moneda",
                                                      "fecha", "numero_operacion", "destinatario", "confianza",
                                                      "observaciones")},
        "verificaciones": [f"{r['regla']}: {r['resultado']} — {r['detalle']}" for r in ver["reglas"]],
    }
    modelo = os.environ["GROQ_MODELO_TEXTO"]
    ia = chat_json(modelo, PROMPT.format(datos=json.dumps(datos, ensure_ascii=False, default=str), minimo=minimo))
    propuesto = str(ia.get("semaforo", "")).lower()
    semaforo = propuesto if NIVEL.get(propuesto, -1) > NIVEL[minimo] else minimo
    if semaforo == "rojo" and minimo != "rojo":   # sin discrepancia dura el agente solo puede escalar a revisión
        semaforo = "amarillo"
    justificacion = str(ia.get("justificacion") or "").strip()[:600] or "Sin justificación del agente."
    motivo = None
    if semaforo == "rojo":
        motivo = (ver["discrepancias_duras"] or [None])[0] or str(ia.get("motivo_rechazo") or "").strip()[:300] \
            or "El comprobante no corresponde a la operación registrada."
    return {"semaforo": semaforo, "semaforo_minimo": minimo, "semaforo_agente": propuesto or None,
            "ruta": RUTA[semaforo], "justificacion": justificacion, "motivo_rechazo": motivo,
            "alerta_cumplimiento": alerta, "monto_usd": usd, "modelo": modelo}


def handler(event, context=None):
    res = evaluar(event["operacion"], event["extraccion"], event["verificacion"])
    log("riesgo_evaluado", id_operacion=event["operacion"].get("id_operacion"), semaforo=res["semaforo"],
        minimo=res["semaforo_minimo"], agente=res["semaforo_agente"], ruta=res["ruta"])
    return res

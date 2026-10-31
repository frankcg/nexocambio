"""
NexoGuard — Verificación de coincidencia  (AWS Lambda · Python 3.12 · paso VerificarCoincidencia)

Reglas DETERMINISTAS (sin IA): compara lo que leyó el Agente Extractor con la operación registrada.
Cada regla devuelve cumple / no_cumple / no_concluyente y su gravedad:
  rechazo     → si no cumple con buena confianza de lectura, la operación se rechaza
  revision    → si no cumple o no es concluyente, va a revisión humana
  informativa → solo se muestra al operador

Consulta (solo lectura) el GSI numero-operacion-index de nexo-validaciones para detectar
comprobantes reutilizados.
"""
import os
import re
import unicodedata
from datetime import date, timedelta

import boto3
from boto3.dynamodb.conditions import Key

from nexo_common import log

CONFIANZA_MINIMA = 0.80
TOLERANCIA_MONTO = 0.01

# Cuentas y CCI de NexoCambio — FICTICIAS (misma fuente que frontend/src/app/features/operar/cuentas-nexo.ts)
CUENTAS_NEXO = {
    "PEN": ["193-2458710-0-39", "002-193-002458710039-14", "200-3001845527", "003-200-003001845527-38",
            "0011-0174-0100073152", "011-174-000100073152-86", "000-4127785", "009-170-000004127785-52"],
    "USD": ["193-2458711-1-47", "002-193-002458711147-17", "200-3001845534", "003-200-003001845534-31",
            "0011-0174-0100073160", "011-174-000100073160-81", "000-4127793", "009-170-000004127793-56"],
    "EUR": ["193-2458712-2-55", "002-193-002458712255-10"],
}


def _digitos(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


def _plano(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def regla(nombre, resultado, gravedad, detalle):
    return {"regla": nombre, "resultado": resultado, "gravedad": gravedad, "detalle": detalle}


def r_reconocido(ex):
    if ex.get("es_comprobante") and ex.get("legible") and ex.get("confianza", 0) >= CONFIANZA_MINIMA:
        return regla("comprobante_reconocido", "cumple", "revision", f"Lectura confiable ({ex['confianza']:.2f}).")
    if ex.get("es_comprobante") is False:
        return regla("comprobante_reconocido", "no_cumple", "revision", "La imagen no parece un comprobante bancario.")
    return regla("comprobante_reconocido", "no_cumple", "revision",
                 f"Lectura no concluyente (confianza {float(ex.get('confianza') or 0):.2f}). {ex.get('observaciones', '')}".strip())


def r_monto(ex, op):
    if ex.get("monto") is None:
        return regla("monto", "no_concluyente", "rechazo", "No se pudo leer el monto.")
    esperado = float(op["monto_origen"])
    if abs(float(ex["monto"]) - esperado) <= TOLERANCIA_MONTO:
        return regla("monto", "cumple", "rechazo", f"Monto {ex['monto']:,.2f} coincide con la operación.")
    return regla("monto", "no_cumple", "rechazo",
                 f"El comprobante indica {ex['monto']:,.2f} y la operación es por {esperado:,.2f}.")


def r_moneda(ex, op):
    if not ex.get("moneda"):
        return regla("moneda", "no_concluyente", "rechazo", "No se pudo leer la moneda.")
    if ex["moneda"] == op["moneda_origen"]:
        return regla("moneda", "cumple", "rechazo", f"Moneda {ex['moneda']} coincide.")
    return regla("moneda", "no_cumple", "rechazo",
                 f"El comprobante está en {ex['moneda']} y la operación en {op['moneda_origen']}.")


def r_cuenta_destino(ex, op):
    if (op.get("origen") or {}).get("tipo") == "wallet":
        return regla("cuenta_destino", "no_concluyente", "rechazo", "Transferencia cripto: se verifica manualmente.")
    visibles = _digitos(ex.get("cuenta_destino"))
    es_nexo = "nexocambio" in _plano(ex.get("destinatario"))
    cuentas = [_digitos(c) for c in CUENTAS_NEXO.get(op["moneda_origen"], [])]
    coincide = len(visibles) >= 2 and any(c.endswith(visibles) for c in cuentas)
    if coincide or (es_nexo and not visibles):
        return regla("cuenta_destino", "cumple", "rechazo", "El destino es una cuenta de NexoCambio.")
    if not visibles and not ex.get("destinatario"):
        return regla("cuenta_destino", "no_concluyente", "rechazo", "No se pudo leer la cuenta de destino.")
    return regla("cuenta_destino", "no_cumple", "rechazo",
                 f"El dinero se envió a {ex.get('destinatario') or 'otro titular'} "
                 f"(cuenta {ex.get('cuenta_destino') or 'no visible'}), que no es una cuenta de NexoCambio "
                 f"en {op['moneda_origen']}.")


def r_duplicado(ex, op):
    nro = ex.get("numero_operacion")
    if not nro:
        return regla("numero_operacion_unico", "no_concluyente", "rechazo", "No se pudo leer el número de operación.")
    tabla = boto3.resource("dynamodb").Table(os.environ["TABLE_VALIDACIONES"])
    items = tabla.query(IndexName="numero-operacion-index", KeyConditionExpression=Key("numero_operacion").eq(nro))["Items"]
    otras = sorted({i["id_operacion"] for i in items if i["id_operacion"] != op["id_operacion"]})
    if otras:
        return regla("numero_operacion_unico", "no_cumple", "rechazo",
                     f"El número de operación {nro} ya se usó en la operación {otras[0]}.")
    return regla("numero_operacion_unico", "cumple", "rechazo", f"Número de operación {nro} no registrado antes.")


def r_fecha(ex, op):
    try:
        f = date.fromisoformat(str(ex.get("fecha")))
    except ValueError:
        return regla("fecha", "no_concluyente", "revision", "No se pudo leer la fecha del comprobante.")
    creada = date.fromisoformat(op["fecha_operacion"][:10])
    if f < creada - timedelta(days=1):
        return regla("fecha", "no_cumple", "revision", f"El comprobante ({f}) es anterior a la operación ({creada}).")
    if f > date.today() + timedelta(days=1):
        return regla("fecha", "no_cumple", "revision", f"El comprobante tiene una fecha futura ({f}).")
    return regla("fecha", "cumple", "revision", f"Fecha {f} válida.")


def r_banco_origen(ex, op):
    declarado = (op.get("origen") or {}).get("banco")
    if not ex.get("banco_origen") or not declarado:
        return regla("banco_origen", "no_concluyente", "informativa", "No se pudo comparar el banco de origen.")
    if _plano(ex["banco_origen"]) == _plano(declarado):
        return regla("banco_origen", "cumple", "informativa", f"Banco de origen {declarado} coincide.")
    return regla("banco_origen", "no_cumple", "informativa",
                 f"Se declaró {declarado} pero el comprobante es de {ex['banco_origen']}.")


def verificar(op: dict, ex: dict) -> dict:
    reglas = [r_reconocido(ex), r_monto(ex, op), r_moneda(ex, op), r_cuenta_destino(ex, op),
              r_duplicado(ex, op), r_fecha(ex, op), r_banco_origen(ex, op)]
    confiable = reglas[0]["resultado"] == "cumple"
    duras = [r for r in reglas if r["gravedad"] == "rechazo" and r["resultado"] == "no_cumple"]
    revisar = [r for r in reglas if r["gravedad"] in ("rechazo", "revision") and r["resultado"] != "cumple"]
    return {"reglas": reglas, "lectura_confiable": confiable,
            "discrepancias_duras": [r["detalle"] for r in duras] if confiable else [],
            "motivos_revision": [r["detalle"] for r in revisar if r not in duras or not confiable],
            "todo_cumple": not revisar}


def handler(event, context=None):
    res = verificar(event["operacion"], event["extraccion"])
    log("verificacion", id_operacion=event["operacion"].get("id_operacion"), todo_cumple=res["todo_cumple"],
        duras=len(res["discrepancias_duras"]))
    return res

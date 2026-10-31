"""
NexoGuard — Conciliación con el banco  (AWS Lambda · Python 3.12 · paso ConciliarConBanco)

Groq solo ve la imagen: no puede saber si el dinero llegó. Este paso le pregunta al BANCO
(API bancaria simulada, por HTTPS y con su propia clave) si existe el depósito en una cuenta de
NexoCambio. El workflow lo repite con esperas (estado Wait) porque una interbancaria puede tardar.

Coincidencia:
  total    → hay un depósito con el N° de operación leído, mismo monto y moneda que la operación
  parcial  → hay un depósito con ese N° pero otro monto/moneda, o no se leyó el N° y hay un
             depósito de hoy por el mismo monto en una cuenta de NexoCambio
  ninguna  → no hay depósito (comprobante falso o transferencia aún no acreditada)

Entrada: {operacion, extraccion, intento}   Salida: {coincidencia, encontrado, detalle, deposito,
         intento, max_intentos, espera_seg}
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

import nexo_cuentas
from nexo_common import log

TOLERANCIA = 0.01


class BancoError(Exception):
    """El banco no respondió: el Catch del workflow envía la operación a revisión."""


def _consultar(**params) -> list:
    url = os.environ["BANCO_API_URL"].rstrip("/") + "/depositos?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"x-banco-key": os.environ["BANCO_KEY"], "User-Agent": "nexoguard/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)["depositos"]
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as e:
        raise BancoError(f"Banco no disponible: {e}")


def _fmt(monto, moneda) -> str:
    return f"{moneda} {float(monto):,.2f}"


def conciliar(op: dict, ex: dict) -> dict:
    moneda, esperado = op["moneda_origen"], float(op["monto_origen"])
    if (op.get("origen") or {}).get("tipo") == "wallet":
        return {"coincidencia": "no_aplica", "detalle": "Transferencia cripto: la conciliación es manual.", "deposito": None}
    cuentas = set(nexo_cuentas.cuentas(moneda))
    nro = ex.get("numero_operacion")
    if nro:
        todas = {c for m in nexo_cuentas.CUENTAS for c in nexo_cuentas.cuentas(m)}
        deps = [d for d in _consultar(numero_operacion=nro) if d["cuenta"] in todas]
        if not deps:
            return {"coincidencia": "ninguna", "deposito": None,
                    "detalle": f"No hay ningún depósito con el N° {nro} en las cuentas de NexoCambio."}
        d = deps[0]
        if d["moneda"] == moneda and abs(float(d["monto"]) - esperado) <= TOLERANCIA and d["cuenta"] in cuentas:
            return {"coincidencia": "total", "deposito": d,
                    "detalle": f"Depósito confirmado en el banco: {_fmt(d['monto'], d['moneda'])} · N° {nro} · {d['fecha']}."}
        return {"coincidencia": "parcial", "deposito": d,
                "detalle": f"En el banco llegó {_fmt(d['monto'], d['moneda'])} con el N° {nro}, "
                           f"pero la operación es por {_fmt(esperado, moneda)}."}
    # Sin N° legible: busca depósitos de la fecha por el mismo monto en las cuentas de NexoCambio
    fecha = ex.get("fecha") or op["fecha_operacion"][:10]
    candidatos = [d for c in cuentas for d in _consultar(cuenta=c, fecha=fecha)
                  if d["moneda"] == moneda and abs(float(d["monto"]) - esperado) <= TOLERANCIA]
    if candidatos:
        d = candidatos[0]
        return {"coincidencia": "parcial", "deposito": d,
                "detalle": f"No se leyó el N° del comprobante; hay {len(candidatos)} depósito(s) del {fecha} por "
                           f"{_fmt(esperado, moneda)} (p. ej. N° {d['numero_operacion']}). Confirmar manualmente."}
    return {"coincidencia": "ninguna", "deposito": None,
            "detalle": f"No hay depósitos del {fecha} por {_fmt(esperado, moneda)} en las cuentas de NexoCambio."}


def handler(event, context=None):
    intento = int(event.get("intento") or 0) + 1
    res = conciliar(event["operacion"], event["extraccion"])
    res.update(intento=intento, encontrado=res["coincidencia"] in ("total", "parcial", "no_aplica"),
               max_intentos=int(os.environ.get("MAX_INTENTOS", "4")), espera_seg=int(os.environ.get("ESPERA_SEG", "30")))
    if res["deposito"]:  # JSON puro para Step Functions
        res["deposito"] = json.loads(json.dumps(res["deposito"], default=float))
    log("conciliacion", id_operacion=event["operacion"].get("id_operacion"), intento=intento,
        coincidencia=res["coincidencia"])
    return res

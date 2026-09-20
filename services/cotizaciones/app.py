"""
Microservicio 1 — COTIZACIONES  (AWS Lambda · Python 3.12)

Responsabilidad: calcular y registrar la cotización de una operación de
Casa de Cambio o Cripto, con vigencia limitada (por defecto 5 minutos).

Base de datos propia (Amazon DynamoDB):
  · nexo-<stage>-tasas          PK moneda      → precio de referencia en USD de cada moneda/activo
  · nexo-<stage>-cotizaciones   PK id_cotizacion → cotizaciones emitidas (TTL automático)

Rutas HTTP (API Gateway):
  POST /cotizar                 (pública) → calcula y registra una cotización

Invocación interna (Lambda → Lambda, no expuesta en internet):
  {"accion": "obtener", "id_cotizacion": "COT-XXXXXXXX"}   lo usa el microservicio Operaciones
"""
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

import boto3
from botocore.exceptions import ClientError

from nexo_common import (ApiError, ahora, cuerpo_json, iso, log, manejar,
                         nuevo_id, requeridos)

# ---------------------------------------------------------------- configuración
CASA = ("PEN", "USD", "EUR")
CRIPTO_ACTIVOS = ("USDT", "USDC", "BTC", "ETH")
MONEDAS = {
    "casa": CASA,
    "cripto": ("PEN", "USD") + CRIPTO_ACTIVOS,
}
DECIMALES = {"PEN": 2, "USD": 2, "EUR": 2, "USDT": 2, "USDC": 2, "BTC": 6, "ETH": 5}
# Precio de referencia (USD por 1 unidad). Se usa solo si no hay tasas en vivo ni en caché.
TASAS_REFERENCIALES = {
    "USD": Decimal("1"), "PEN": Decimal("0.2954"), "EUR": Decimal("1.085"),
    "USDT": Decimal("1"), "USDC": Decimal("1"), "BTC": Decimal("98500"), "ETH": Decimal("3450"),
}
MONTO_MINIMO_USD = Decimal("10")
MONTO_MAXIMO_USD = Decimal("1000000")


def _cfg():
    return {
        "validez": int(os.environ.get("VALIDEZ_SEG", "300")),
        "ttl_tasas": int(os.environ.get("TASAS_TTL_SEG", "300")),
        "en_vivo": os.environ.get("USAR_TASAS_EN_VIVO", "true").lower() == "true",
        "spread": {"casa": Decimal(os.environ.get("SPREAD_CASA", "0.0045")),
                   "cripto": Decimal(os.environ.get("SPREAD_CRIPTO", "0.012"))},
        "pref_usd": Decimal(os.environ.get("PREFERENCIAL_DESDE_USD", "5000")),
        "factor_pref": Decimal("0.6"),  # el spread baja 40 % en montos altos
    }


def _dynamo():
    return boto3.resource("dynamodb")


def _t_cot():
    return _dynamo().Table(os.environ["TABLE_COTIZACIONES"])


def _t_tasas():
    return _dynamo().Table(os.environ["TABLE_TASAS"])


# ------------------------------------------------------------------- tasas
def _http_json(url: str, timeout=2.5):
    req = urllib.request.Request(url, headers={"User-Agent": "NexoCambio/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (URL fija, https)
        return json.loads(r.read().decode())


def consultar_tasas_en_vivo() -> dict:
    """Consulta fuentes públicas (sin API key). Devuelve {moneda: Decimal(USD por unidad)}.
    Cada fuente es independiente: si una falla se devuelve lo que sí se obtuvo."""
    out = {}
    try:  # divisas
        d = _http_json("https://open.er-api.com/v6/latest/USD")
        for m in ("PEN", "EUR"):
            out[m] = (Decimal(1) / Decimal(str(d["rates"][m]))).quantize(Decimal("0.00000001"))
        out["USD"] = Decimal(1)
    except Exception as e:  # noqa: BLE001
        log("tasas_fx_no_disponible", error=type(e).__name__)
    try:  # cripto
        c = _http_json("https://api.coingecko.com/api/v3/simple/price"
                       "?ids=bitcoin,ethereum,tether,usd-coin&vs_currencies=usd")
        out["BTC"] = Decimal(str(c["bitcoin"]["usd"]))
        out["ETH"] = Decimal(str(c["ethereum"]["usd"]))
        out["USDT"] = Decimal(str(c["tether"]["usd"]))
        out["USDC"] = Decimal(str(c["usd-coin"]["usd"]))
    except Exception as e:  # noqa: BLE001
        log("tasas_cripto_no_disponible", error=type(e).__name__)
    return out


def obtener_tasas() -> tuple[dict, str]:
    """Lee las tasas de DynamoDB; si están vencidas intenta refrescarlas (lazy refresh).
    Devuelve ({moneda: usd}, fuente) con fuente ∈ {en_vivo, cache, referencial}:
      en_vivo     todas las tasas se actualizaron dentro de la ventana de vigencia
      cache       se usa la última tasa guardada (la fuente externa no respondió)
      referencial se usan valores fijos de respaldo (sin conexión y sin historial)
    """
    cfg = _cfg()
    tabla = _t_tasas()
    ahora_s = int(time.time())
    guardadas = {it["moneda"]: it for it in tabla.scan().get("Items", []) if it["moneda"] != "_meta"}

    def estado(m):
        g = guardadas.get(m)
        if g is None:
            return "referencial"
        return "en_vivo" if ahora_s - int(g["actualizado"]) <= cfg["ttl_tasas"] else "cache"

    if cfg["en_vivo"] and any(estado(m) != "en_vivo" for m in TASAS_REFERENCIALES):
        meta = tabla.get_item(Key={"moneda": "_meta"}).get("Item", {})
        # evita reintentar en cada request si la fuente externa está caída (1 intento/min)
        if ahora_s - int(meta.get("ultimo_intento", 0)) >= 60:
            tabla.put_item(Item={"moneda": "_meta", "ultimo_intento": ahora_s})
            for m, usd in consultar_tasas_en_vivo().items():
                item = {"moneda": m, "usd": usd, "fuente": "en_vivo", "actualizado": ahora_s}
                tabla.put_item(Item=item)
                guardadas[m] = item

    estados = {m: estado(m) for m in TASAS_REFERENCIALES}
    fuente = ("referencial" if "referencial" in estados.values()
              else "cache" if "cache" in estados.values() else "en_vivo")
    usd = {m: (guardadas[m]["usd"] if m in guardadas else ref) for m, ref in TASAS_REFERENCIALES.items()}
    return usd, fuente


# ----------------------------------------------------------------- negocio
def _cuantizar(valor: Decimal, moneda: str) -> Decimal:
    return valor.quantize(Decimal(1).scaleb(-DECIMALES[moneda]), rounding=ROUND_HALF_UP)


def _validar(datos: dict):
    requeridos(datos, ["modalidad", "moneda_origen", "moneda_destino", "monto_origen"])
    mod, o, d = datos["modalidad"], datos["moneda_origen"], datos["moneda_destino"]
    if mod not in MONEDAS:
        raise ApiError(400, "La modalidad debe ser 'casa' o 'cripto'.", "modalidad_invalida")
    for m in (o, d):
        if m not in MONEDAS[mod]:
            raise ApiError(422, f"La moneda {m} no está disponible en la modalidad {mod}.", "moneda_no_disponible")
    if o == d:
        raise ApiError(422, "Elige monedas distintas para enviar y recibir.", "monedas_iguales")
    if mod == "cripto" and o not in CRIPTO_ACTIVOS and d not in CRIPTO_ACTIVOS:
        raise ApiError(422, "En la modalidad Cripto uno de los extremos debe ser un criptoactivo.", "sin_cripto")
    try:
        monto = Decimal(str(datos["monto_origen"]))
    except Exception:  # noqa: BLE001
        raise ApiError(400, "El monto debe ser numérico.", "monto_invalido")
    if not monto.is_finite() or monto <= 0:
        raise ApiError(422, "Ingresa un monto mayor a cero.", "monto_invalido")
    return mod, o, d, monto


def cotizar(event):
    mod, o, d, monto = _validar(cuerpo_json(event))
    cfg = _cfg()
    tasas, fuente = obtener_tasas()

    monto_usd = monto * tasas[o]
    if monto_usd < MONTO_MINIMO_USD:
        raise ApiError(422, "El monto mínimo equivale a US$ 10.", "monto_minimo")
    if monto_usd > MONTO_MAXIMO_USD:
        raise ApiError(422, "El monto supera el máximo permitido por operación (US$ 1,000,000).", "monto_maximo")

    preferencial = monto_usd >= cfg["pref_usd"]
    spread = cfg["spread"][mod] * (cfg["factor_pref"] if preferencial else 1)
    tasa = ((tasas[o] / tasas[d]) * (1 - spread)).quantize(Decimal("0.00000001"))
    monto_destino = _cuantizar(monto * tasa, d)

    t0 = ahora()
    expira = int(t0.timestamp()) + cfg["validez"]
    cot = {
        "id_cotizacion": nuevo_id("COT-"),
        "modalidad": mod, "moneda_origen": o, "moneda_destino": d,
        "monto_origen": monto, "tasa": tasa, "tasa_preferencial": preferencial,
        "monto_destino": monto_destino, "fuente_tasas": fuente,
        "fecha_cotizacion": iso(t0),
        "fecha_expiracion": iso(datetime.fromtimestamp(expira, tz=timezone.utc)),
        "expira_epoch": expira,
        "ttl": expira + 3600,  # DynamoDB TTL elimina la cotización 1 h después de vencer
    }
    _t_cot().put_item(Item=cot)
    log("cotizacion_creada", id=cot["id_cotizacion"], modalidad=mod, par=f"{o}/{d}", fuente=fuente)
    return 201, {k: v for k, v in cot.items() if k not in ("expira_epoch", "ttl")}


# ------------------------------------------------------- invocación interna
def obtener_cotizacion(id_cotizacion: str) -> dict:
    it = _t_cot().get_item(Key={"id_cotizacion": id_cotizacion}).get("Item")
    if not it:
        return {"ok": False, "status": 404, "mensaje": "No encontramos la cotización."}
    restante = int(it["expira_epoch"]) - int(time.time())
    it = {k: v for k, v in it.items() if k != "ttl"}
    it["segundos_restantes"] = restante
    return {"ok": True, "cotizacion": it}


_http = manejar({"POST /cotizar": cotizar})


def handler(event, context=None):
    if event.get("accion") == "obtener":  # Lambda → Lambda (microservicio Operaciones)
        try:
            res = obtener_cotizacion(str(event.get("id_cotizacion", "")))
            return json.loads(json.dumps(res, default=lambda o: float(o) if isinstance(o, Decimal) else str(o)))
        except ClientError as e:
            log("error_dynamo", codigo=e.response["Error"]["Code"])
            return {"ok": False, "status": 500, "mensaje": "Error consultando cotización."}
    return _http(event, context)

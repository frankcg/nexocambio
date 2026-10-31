"""
NexoGuard — Agente Extractor  (AWS Lambda · Python 3.12 · paso ExtraerComprobante)

Lee el comprobante desde S3 y le pide a Groq (modelo con visión, sin memoria) que extraiga
sus datos en JSON. Normaliza la salida para que las reglas de verificación la usen tal cual.
No decide nada: si la lectura no es concluyente, lo dice y el workflow lo enviará a revisión.

Entrada (Step Functions): {"operacion": {..., "ruta_comprobante": "s3://bucket/clave", "comprobante_tipo": "image/png"}}
Salida: {es_comprobante, legible, banco_origen, monto, moneda, fecha, hora, numero_operacion,
         destinatario, cuenta_destino, banco_destino, confianza, observaciones, modelo}
"""
import base64
import os
import re

import boto3

from nexo_common import log
from nexo_groq import chat_json

PROMPT = """Eres un extractor de datos de comprobantes de transferencias bancarias peruanas.
Analiza la imagen y responde SOLO con un JSON con estas claves:
{"es_comprobante": bool, "legible": bool, "banco_origen": str|null, "monto": number|null,
 "moneda": "PEN"|"USD"|"EUR"|null, "fecha": "YYYY-MM-DD"|null, "hora": "HH:MM"|null,
 "numero_operacion": str|null, "destinatario": str|null, "cuenta_destino": str|null,
 "banco_destino": str|null, "confianza": number entre 0 y 1, "observaciones": str}
El banco de origen suele ser el nombre que aparece en el encabezado del comprobante.
"S/" es PEN, "US$" o "$" es USD y "€" es EUR. Si la imagen no es un comprobante bancario o no
se lee, indica es_comprobante/legible en false y deja null lo que no puedas leer. No inventes
datos. Ignora marcas de agua. Las observaciones deben ser breves (máximo 2 oraciones)."""

MAX_IMAGEN = 3 * 1024 * 1024        # Groq acepta imágenes en base64 de hasta ~4 MB
BANCOS = {"bcp": "BCP", "interbank": "Interbank", "bbva": "BBVA", "scotiabank": "Scotiabank",
          "banbif": "BanBif", "pichincha": "Banco Pichincha"}


def no_concluyente(motivo: str) -> dict:
    return {"es_comprobante": None, "legible": False, "banco_origen": None, "monto": None, "moneda": None,
            "fecha": None, "hora": None, "numero_operacion": None, "destinatario": None, "cuenta_destino": None,
            "banco_destino": None, "confianza": 0, "observaciones": motivo, "modelo": None}


def _banco(v):
    if not v:
        return None
    t = str(v).lower()
    return next((nombre for clave, nombre in BANCOS.items() if clave in t), str(v).strip())


def _numero(v):
    try:
        return round(float(str(v).replace(",", "")), 2) if v is not None else None
    except ValueError:
        return None


def normalizar(d: dict) -> dict:
    """Deja la respuesta del modelo con tipos y formatos estables."""
    conf = _numero(d.get("confianza"))
    moneda = str(d.get("moneda") or "").upper() or None
    nro = re.sub(r"\D", "", str(d.get("numero_operacion") or "")) or None
    return {
        "es_comprobante": bool(d.get("es_comprobante")), "legible": bool(d.get("legible")),
        "banco_origen": _banco(d.get("banco_origen")), "monto": _numero(d.get("monto")),
        "moneda": moneda if moneda in {"PEN", "USD", "EUR"} else None,
        "fecha": d.get("fecha") or None, "hora": d.get("hora") or None, "numero_operacion": nro,
        "destinatario": (str(d.get("destinatario")).strip() or None) if d.get("destinatario") else None,
        "cuenta_destino": (str(d.get("cuenta_destino")).strip() or None) if d.get("cuenta_destino") else None,
        "banco_destino": _banco(d.get("banco_destino")),
        "confianza": max(0.0, min(1.0, conf)) if conf is not None else 0.0,
        "observaciones": str(d.get("observaciones") or "")[:400],
    }


def handler(event, context=None):
    op = event["operacion"]
    m = re.match(r"^s3://([^/]+)/(.+)$", op.get("ruta_comprobante") or "")
    if not m:
        return no_concluyente("La operación no tiene comprobante adjunto.")
    tipo = op.get("comprobante_tipo", "")
    if not tipo.startswith("image/"):
        return no_concluyente("El comprobante es un PDF; la lectura automática solo admite imágenes.")
    datos = boto3.client("s3").get_object(Bucket=m.group(1), Key=m.group(2))["Body"].read()
    if len(datos) > MAX_IMAGEN:
        return no_concluyente("La imagen supera el tamaño que admite la lectura automática.")

    modelo = os.environ["GROQ_MODELO_VISION"]
    b64 = base64.b64encode(datos).decode()
    crudo = chat_json(modelo, [{"type": "text", "text": PROMPT},
                               {"type": "image_url", "image_url": {"url": f"data:{tipo};base64,{b64}"}}])
    res = {**normalizar(crudo), "modelo": modelo}
    log("comprobante_extraido", id_operacion=op.get("id_operacion"), legible=res["legible"],
        es_comprobante=res["es_comprobante"], confianza=res["confianza"])
    return res

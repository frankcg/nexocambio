"""
Microservicio 3 — OPERACIONES  (AWS Lambda · Python 3.12)

Responsabilidad: registrar las operaciones de cambio del cliente, guardar el
comprobante de transferencia, mantener el estado y permitir consultar el
historial.

Base de datos propia:
  · Amazon DynamoDB  nexo-<stage>-operaciones
        PK id_operacion   ·   GSI cliente-fecha-index (id_cliente, fecha_operacion)
  · Amazon S3        bucket privado de comprobantes
        clave  comprobantes/<id_cliente>/<id_operacion>/<archivo>

Estados: [Pendiente de comprobante] (interno, no se lista) →
         Pendiente de validación → En proceso → Procesada | Rechazada

Rutas HTTP (todas requieren JWT salvo las de back-office, que usan x-admin-key):
  POST  /operaciones                          registra una operación desde una cotización vigente
  POST  /operaciones/{id_operacion}/comprobante   adjunta el comprobante (imagen/PDF, base64)
  GET   /operaciones                          lista las operaciones del cliente autenticado
  GET   /operaciones/{id_operacion}           detalle (incluye URL temporal del comprobante)
  PATCH /operaciones/{id_operacion}/estado    [back-office simulado] avanza el estado
  GET   /operaciones/admin                    [back-office simulado] lista TODAS las operaciones
  GET   /operaciones/{id_operacion}/admin     [back-office simulado] detalle de cualquier operación

Comunicación entre microservicios: invoca a Cotizaciones (Lambda → Lambda) para
validar la cotización y NO confía en tasa/montos enviados por el navegador.
"""
import base64
import binascii
import hmac
import json
import os
import re
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.config import Config
from botocore.exceptions import ClientError

from nexo_common import (ApiError, ahora, cuerpo_json, encabezado, exigir_sesion,
                         iso, log, manejar, parametro_ruta, requeridos, texto)

BORRADOR = "Pendiente de comprobante"
PEND = "Pendiente de validación"
PROC = "En proceso"
OK = "Procesada"
RECH = "Rechazada"
TRANSICIONES = {PEND: {PROC, RECH}, PROC: {OK, RECH}}

FIAT = {"PEN", "USD", "EUR"}
BANCOS = {"BCP", "Interbank", "BBVA", "Scotiabank", "BanBif", "Banco Pichincha"}
TIPOS_CUENTA = {"Ahorros", "Corriente"}
REDES = {"USDT": {"TRON (TRC20)", "Ethereum (ERC20)"}, "USDC": {"Ethereum (ERC20)", "Solana"},
         "BTC": {"Bitcoin"}, "ETH": {"Ethereum (ERC20)"}}
RE_CUENTA = re.compile(r"^\d{10,20}$")
RE_WALLET = re.compile(r"^[A-Za-z0-9]{26,64}$")

TIPOS_ARCHIVO = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "application/pdf": "pdf"}


def _cfg():
    return {"gracia": int(os.environ.get("GRACIA_SEG", "600")),
            "max_bytes": int(os.environ.get("MAX_COMPROBANTE_BYTES", str(4 * 1024 * 1024))),
            "url_seg": int(os.environ.get("URL_COMPROBANTE_SEG", "900"))}


def _tabla():
    return boto3.resource("dynamodb").Table(os.environ["TABLE_OPERACIONES"])


def _s3():
    return boto3.client("s3", config=Config(signature_version="s3v4"))


# ------------------------------------------------ comunicación con Cotizaciones
def cotizaciones_obtener(id_cotizacion: str) -> dict:
    """Lambda → Lambda. Devuelve la cotización o lanza ApiError."""
    try:
        r = boto3.client("lambda").invoke(
            FunctionName=os.environ["FN_COTIZACIONES"], InvocationType="RequestResponse",
            Payload=json.dumps({"accion": "obtener", "id_cotizacion": id_cotizacion}).encode())
        data = json.loads(r["Payload"].read())
    except Exception as e:  # noqa: BLE001
        log("cotizaciones_no_disponible", error=type(e).__name__)
        raise ApiError(502, "No pudimos validar la cotización. Inténtalo nuevamente.", "servicio_no_disponible")
    if r.get("FunctionError") or not data.get("ok"):
        raise ApiError(404, data.get("mensaje", "No encontramos la cotización."), "cotizacion_no_encontrada")
    return data["cotizacion"]


# ------------------------------------------------------------------ utilidades
def _dec(x) -> Decimal:
    return Decimal(str(x))


def _publico(op: dict) -> dict:
    return dict(op)


def _exigir_admin(event) -> None:
    """Protege las rutas de back-office simulado con la cabecera x-admin-key."""
    admin = os.environ.get("ADMIN_KEY", "")
    clave = encabezado(event, "x-admin-key") or ""
    if not admin or not hmac.compare_digest(clave, admin):
        raise ApiError(403, "Acceso restringido al back-office.", "prohibido")


def _con_comprobante(op: dict, cfg: dict) -> dict:
    op = _publico(op)
    bucket, clave = _partir_ruta_s3(op.get("ruta_comprobante"))
    if bucket:  # URL temporal firmada: el bucket nunca es público
        op["comprobante_url"] = _s3().generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": clave}, ExpiresIn=cfg["url_seg"])
    return op


def _validar_extremo(e, moneda: str, rol: str) -> dict:
    """Valida origen/destino: banco para monedas fiat, wallet para criptoactivos."""
    if not isinstance(e, dict):
        raise ApiError(400, f"Datos de {rol} inválidos.", "extremo_invalido")
    es_fiat = moneda in FIAT
    if es_fiat:
        if e.get("tipo") != "banco":
            raise ApiError(422, f"Para {moneda} el {rol} debe ser una cuenta bancaria.", "extremo_invalido")
        if e.get("banco") not in BANCOS:
            raise ApiError(422, f"Selecciona un banco válido en el {rol}.", "banco_invalido")
        out = {"tipo": "banco", "banco": e["banco"]}
        if rol == "destino":
            numero = re.sub(r"[\s-]", "", str(e.get("numero", "")))
            if not RE_CUENTA.match(numero):
                raise ApiError(422, "Ingresa entre 10 y 20 dígitos (número de cuenta o CCI).", "cuenta_invalida")
            if e.get("tipo_cuenta") not in TIPOS_CUENTA:
                raise ApiError(422, "Selecciona el tipo de cuenta.", "tipo_cuenta_invalido")
            out.update({"tipo_cuenta": e["tipo_cuenta"], "numero": numero,
                        "titular": texto(e.get("titular", ""), "titular", 2, 150)})
        return out
    if e.get("tipo") != "wallet":
        raise ApiError(422, f"Para {moneda} el {rol} debe ser una billetera cripto.", "extremo_invalido")
    if e.get("red") not in REDES.get(moneda, set()):
        raise ApiError(422, f"Selecciona una red válida para {moneda}.", "red_invalida")
    out = {"tipo": "wallet", "red": e["red"]}
    if rol == "destino":
        if not RE_WALLET.match(str(e.get("direccion", ""))):
            raise ApiError(422, "La dirección de la billetera no parece válida.", "wallet_invalida")
        out["direccion"] = e["direccion"]
    return out


def _partir_ruta_s3(ruta: str):
    m = re.match(r"^s3://([^/]+)/(.+)$", ruta or "")
    return (m.group(1), m.group(2)) if m else (None, None)


# ---------------------------------------------------------- POST /operaciones
def crear_operacion(event):
    claims = exigir_sesion(event)
    d = cuerpo_json(event)
    requeridos(d, ["id_cotizacion", "origen", "destino"])
    cot = cotizaciones_obtener(str(d["id_cotizacion"]))
    cfg = _cfg()

    if int(cot["segundos_restantes"]) < -cfg["gracia"]:
        raise ApiError(409, "La cotización expiró. Actualiza la tasa para continuar.", "cotizacion_expirada")
    for campo in ("modalidad", "moneda_origen", "moneda_destino"):
        if d.get(campo) not in (None, cot[campo]):
            raise ApiError(422, "Los datos no coinciden con la cotización.", "cotizacion_inconsistente")
    if d.get("monto_origen") is not None and _dec(d["monto_origen"]) != _dec(cot["monto_origen"]):
        raise ApiError(422, "El monto no coincide con la cotización.", "cotizacion_inconsistente")

    origen = _validar_extremo(d["origen"], cot["moneda_origen"], "origen")
    destino = _validar_extremo(d["destino"], cot["moneda_destino"], "destino")

    # id derivado de la cotización → una cotización solo puede usarse UNA vez.
    id_op = "NX-" + str(cot["id_cotizacion"]).split("-", 1)[1]
    op = {
        "id_operacion": id_op, "id_cliente": claims["sub"], "id_cotizacion": cot["id_cotizacion"],
        "modalidad": cot["modalidad"], "moneda_origen": cot["moneda_origen"], "moneda_destino": cot["moneda_destino"],
        "monto_origen": _dec(cot["monto_origen"]), "monto_destino": _dec(cot["monto_destino"]),
        "tasa": _dec(cot["tasa"]), "tasa_preferencial": bool(cot.get("tasa_preferencial", False)),
        "estado": BORRADOR, "fecha_operacion": iso(ahora()), "historial": [],
        "origen": origen, "destino": destino,
    }
    try:
        _tabla().put_item(Item=op, ConditionExpression="attribute_not_exists(id_operacion)")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ApiError(409, "Esta cotización ya fue utilizada. Genera una nueva.", "cotizacion_usada")
        raise
    log("operacion_creada", id_operacion=id_op, id_cliente=claims["sub"])
    return 201, _publico(op)


# ------------------------------------------- POST /operaciones/{id}/comprobante
def _decodificar_archivo(b64: str, tipo: str, max_bytes: int) -> bytes:
    if len(b64) > (max_bytes * 4) // 3 + 8:
        raise ApiError(413, f"El archivo supera el máximo de {max_bytes // (1024 * 1024)} MB.", "archivo_grande")
    try:
        datos = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        raise ApiError(400, "El archivo no está codificado correctamente.", "archivo_invalido")
    if not datos or len(datos) > max_bytes:
        raise ApiError(413, f"El archivo supera el máximo de {max_bytes // (1024 * 1024)} MB.", "archivo_grande")
    firmas = {"image/jpeg": datos.startswith(b"\xff\xd8\xff"), "image/png": datos.startswith(b"\x89PNG\r\n\x1a\n"),
              "application/pdf": datos.startswith(b"%PDF"),
              "image/webp": datos[:4] == b"RIFF" and datos[8:12] == b"WEBP"}
    if not firmas.get(tipo, False):  # el contenido real debe coincidir con el tipo declarado
        raise ApiError(422, "El archivo no coincide con el formato indicado (JPG, PNG, WEBP o PDF).", "archivo_invalido")
    return datos


def _nombre_seguro(nombre: str, ext: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(str(nombre or "")))[-80:] or "comprobante"
    return base if base.lower().endswith("." + ext) else f"{base}.{ext}"


def _cargar_propia(id_op: str, id_cliente: str) -> dict:
    op = _tabla().get_item(Key={"id_operacion": id_op}).get("Item")
    if not op or op["id_cliente"] != id_cliente:  # 404 (no 403) para no revelar existencia
        raise ApiError(404, "No encontramos esta operación en tu cuenta.", "no_encontrada")
    return op


def subir_comprobante(event):
    claims = exigir_sesion(event)
    id_op = parametro_ruta(event, "id_operacion")
    d = cuerpo_json(event)
    requeridos(d, ["nombre_archivo", "content_type", "contenido_base64"])
    tipo = str(d["content_type"]).lower()
    if tipo not in TIPOS_ARCHIVO:
        raise ApiError(422, "Formato no permitido. Usa JPG, PNG, WEBP o PDF.", "formato_no_permitido")
    cfg = _cfg()
    op = _cargar_propia(id_op, claims["sub"])
    if op["estado"] not in (BORRADOR, PEND):
        raise ApiError(409, "Esta operación ya no admite cambios de comprobante.", "estado_invalido")
    datos = _decodificar_archivo(str(d["contenido_base64"]), tipo, cfg["max_bytes"])

    nombre = _nombre_seguro(d["nombre_archivo"], TIPOS_ARCHIVO[tipo])
    bucket = os.environ["BUCKET_COMPROBANTES"]
    clave = f"comprobantes/{claims['sub']}/{id_op}/{nombre}"
    _s3().put_object(Bucket=bucket, Key=clave, Body=datos, ContentType=tipo, ServerSideEncryption="AES256")

    sets = {"estado": PEND, "ruta_comprobante": f"s3://{bucket}/{clave}", "comprobante_nombre": nombre,
            "comprobante_tipo": tipo, "comprobante_tamano": len(datos)}
    nro = d.get("numero_transferencia")
    if nro:
        sets["numero_transferencia"] = texto(str(nro), "numero_transferencia", 1, 40)
    expr = "SET " + ", ".join(f"#{k} = :{k}" for k in sets)
    nombres = {f"#{k}": k for k in sets}
    valores = {f":{k}": v for k, v in sets.items()}
    if op["estado"] == BORRADOR:  # primera vez: registra el hito en el historial
        expr += ", #historial = list_append(if_not_exists(#historial, :vacio), :hito)"
        nombres["#historial"] = "historial"
        valores.update({":vacio": [], ":hito": [{"estado": PEND, "fecha": iso(ahora())}]})
    valores[":actual"] = op["estado"]
    try:
        r = _tabla().update_item(Key={"id_operacion": id_op}, UpdateExpression=expr,
                                 ConditionExpression="#estado_actual = :actual",
                                 ExpressionAttributeNames={**nombres, "#estado_actual": "estado"},
                                 ExpressionAttributeValues=valores, ReturnValues="ALL_NEW")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ApiError(409, "La operación cambió de estado. Actualiza e inténtalo otra vez.", "conflicto")
        raise
    log("comprobante_registrado", id_operacion=id_op, bytes=len(datos), tipo=tipo)
    return 200, _publico(r["Attributes"])


# ----------------------------------------------------------- GET /operaciones
def listar_operaciones(event):
    claims = exigir_sesion(event)
    kwargs = dict(IndexName="cliente-fecha-index", KeyConditionExpression=Key("id_cliente").eq(claims["sub"]),
                  FilterExpression=Attr("estado").ne(BORRADOR), ScanIndexForward=False)
    items = []
    while True:
        r = _tabla().query(**kwargs)
        items += r["Items"]
        if "LastEvaluatedKey" not in r or len(items) >= 200:
            break
        kwargs["ExclusiveStartKey"] = r["LastEvaluatedKey"]
    return 200, {"operaciones": [_publico(i) for i in items[:200]], "total": min(len(items), 200)}


# -------------------------------------------------- GET /operaciones/{id}
def obtener_operacion(event):
    claims = exigir_sesion(event)
    op = _cargar_propia(parametro_ruta(event, "id_operacion"), claims["sub"])
    return 200, _con_comprobante(op, _cfg())


# ------------------------------------------------- GET /operaciones/admin (back-office)
def listar_operaciones_admin(event):
    """Lista TODAS las operaciones (de cualquier cliente) para la cola de revisión del back-office."""
    _exigir_admin(event)
    kwargs = dict(FilterExpression=Attr("estado").ne(BORRADOR))
    items = []
    while True:
        r = _tabla().scan(**kwargs)
        items += r["Items"]
        if "LastEvaluatedKey" not in r or len(items) >= 200:
            break
        kwargs["ExclusiveStartKey"] = r["LastEvaluatedKey"]
    items.sort(key=lambda o: o["fecha_operacion"], reverse=True)
    return 200, {"operaciones": [_publico(i) for i in items[:200]], "total": min(len(items), 200)}


# ------------------------------------------ GET /operaciones/{id}/admin (back-office)
def obtener_operacion_admin(event):
    """Detalle de cualquier operación (sin restricción de dueño) para el back-office."""
    _exigir_admin(event)
    id_op = parametro_ruta(event, "id_operacion")
    op = _tabla().get_item(Key={"id_operacion": id_op}).get("Item")
    if not op:
        raise ApiError(404, "No encontramos la operación.", "no_encontrada")
    return 200, _con_comprobante(op, _cfg())


# ----------------------------------- PATCH /operaciones/{id}/estado (back-office)
def cambiar_estado(event):
    """Simula el back-office (fuera del alcance del MVP del cliente).
    Protegido con la cabecera x-admin-key; si ADMIN_KEY no está definida, la ruta queda deshabilitada."""
    _exigir_admin(event)
    id_op = parametro_ruta(event, "id_operacion")
    d = cuerpo_json(event)
    requeridos(d, ["estado"])
    op = _tabla().get_item(Key={"id_operacion": id_op}).get("Item")
    if not op:
        raise ApiError(404, "No encontramos la operación.", "no_encontrada")
    nuevo = d["estado"]
    if nuevo not in TRANSICIONES.get(op["estado"], set()):
        raise ApiError(409, f"No se puede pasar de '{op['estado']}' a '{nuevo}'.", "transicion_invalida")
    sets = "SET #e = :n, #h = list_append(#h, :hito)"
    nombres = {"#e": "estado", "#h": "historial"}
    valores = {":n": nuevo, ":hito": [{"estado": nuevo, "fecha": iso(ahora())}], ":actual": op["estado"]}
    if nuevo == RECH:
        sets += ", motivo_rechazo = :m"
        valores[":m"] = texto(d.get("motivo_rechazo", ""), "motivo_rechazo", 3, 300)
    try:
        r = _tabla().update_item(Key={"id_operacion": id_op}, UpdateExpression=sets,
                                 ConditionExpression="#e = :actual", ExpressionAttributeNames=nombres,
                                 ExpressionAttributeValues=valores, ReturnValues="ALL_NEW")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ApiError(409, "La operación cambió de estado. Vuelve a consultarla.", "conflicto")
        raise
    log("estado_actualizado", id_operacion=id_op, estado=nuevo)
    return 200, _publico(r["Attributes"])


handler = manejar({
    "POST /operaciones": crear_operacion,
    "GET /operaciones": listar_operaciones,
    "GET /operaciones/admin": listar_operaciones_admin,
    "GET /operaciones/{id_operacion}": obtener_operacion,
    "GET /operaciones/{id_operacion}/admin": obtener_operacion_admin,
    "POST /operaciones/{id_operacion}/comprobante": subir_comprobante,
    "PATCH /operaciones/{id_operacion}/estado": cambiar_estado,
})

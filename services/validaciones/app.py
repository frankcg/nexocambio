"""
Microservicio 4 — VALIDACIONES  (AWS Lambda · Python 3.12) · NexoGuard

Responsabilidad: guardar y exponer el análisis de cada validación automática de comprobantes
(registro auditable) y recibir la decisión del operador para reanudar el workflow.

Base de datos propia:
  · Amazon DynamoDB  nexo-<stage>-validaciones
        PK id_operacion · SK fecha_inicio
        GSI numero-operacion-index (numero_operacion)      → detección de comprobantes duplicados
        GSI estado-fecha-index     (estado, fecha_inicio)  → cola de revisión del back-office

Estados de una validación: en_curso → [en_revision → en_curso] → finalizada

Rutas HTTP:
  GET  /validaciones/{id_operacion}            [JWT, dueño] última validación (vista del cliente)
  GET  /validaciones/{id_operacion}/admin      [x-admin-key] todas las validaciones, detalle completo
  GET  /validaciones/admin?estado=en_revision  [x-admin-key] cola de revisión
  POST /validaciones/{id_operacion}/decision   [x-admin-key] {decision: aprobar|rechazar, motivo?}
                                               → SendTaskSuccess (reanuda Step Functions)

  POST /demo/reiniciar                         [x-admin-key] {incluir_operaciones?, conservar_demo?} reinicia los
                                               datos de prueba: detiene ejecuciones en curso, vacía nexo-validaciones,
                                               reinicia el banco simulado (conserva los depósitos de la demo web salvo
                                               conservar_demo: false) y (opcional) las operaciones

Acciones internas (invocadas por Step Functions, no expuestas en internet):
  {"accion": "iniciar" | "registrar_espera" | "guardar", ...}
"""
import hmac
import json
import os
import urllib.error
import urllib.request
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from nexo_common import (ApiError, ahora, cuerpo_json, encabezado, exigir_sesion, iso, log, manejar,
                         parametro_ruta, texto)

EN_CURSO, EN_REVISION, FINALIZADA = "en_curso", "en_revision", "finalizada"


def _tabla():
    return boto3.resource("dynamodb").Table(os.environ["TABLE_VALIDACIONES"])


def _sfn():
    return boto3.client("stepfunctions")


def _ddb(x):
    """JSON de Step Functions → tipos aceptados por DynamoDB (float → Decimal)."""
    return json.loads(json.dumps(x, default=str), parse_float=Decimal)


def _exigir_admin(event) -> None:
    admin = os.environ.get("ADMIN_KEY", "")
    clave = encabezado(event, "x-admin-key") or ""
    if not admin or not hmac.compare_digest(clave, admin):
        raise ApiError(403, "Acceso restringido al back-office.", "prohibido")


def _sin_token(v: dict) -> dict:
    return {k: x for k, x in v.items() if k != "task_token"}


def _ultima(id_op: str):
    r = _tabla().query(KeyConditionExpression=Key("id_operacion").eq(id_op), ScanIndexForward=False, Limit=1)
    return r["Items"][0] if r["Items"] else None


def _analisis(ev: dict) -> dict:
    """Campos del análisis que se guardan al esperar revisión y al finalizar."""
    ex, ver, rie = ev.get("extraccion") or {}, ev.get("verificacion") or {}, ev.get("riesgo") or {}
    conc = ev.get("conciliacion") or {}
    sets = {"extraccion": _ddb(ex), "verificaciones": _ddb(rie.get("verificaciones") or ver.get("reglas", [])),
            "conciliacion": _ddb({k: conc.get(k) for k in ("coincidencia", "detalle", "deposito", "intento")}),
            "semaforo": rie.get("semaforo"), "justificacion": rie.get("justificacion"), "ruta": rie.get("ruta"),
            "alerta_cumplimiento": bool(rie.get("alerta_cumplimiento")),
            "monto_usd": _ddb(rie.get("monto_usd")), "motivo_sugerido": rie.get("motivo_rechazo"),
            "modelos": {"vision": ex.get("modelo"), "texto": rie.get("modelo")}}
    if ex.get("numero_operacion"):
        sets["numero_operacion"] = ex["numero_operacion"]
    return sets


def _actualizar(id_op: str, fecha: str, sets: dict, quitar=(), condicion=None, valores_extra=None):
    expr = "SET " + ", ".join(f"#{k} = :{k}" for k in sets)
    if quitar:
        expr += " REMOVE " + ", ".join(f"#{k}" for k in quitar)
    nombres = {f"#{k}": k for k in [*sets, *quitar]}
    valores = {f":{k}": v for k, v in sets.items()}
    kw = {}
    if condicion:
        kw["ConditionExpression"] = condicion
        nombres.update({"#task_token": "task_token"} if "task_token" in condicion else {})
        valores.update(valores_extra or {})
    return _tabla().update_item(Key={"id_operacion": id_op, "fecha_inicio": fecha}, UpdateExpression=expr,
                                ExpressionAttributeNames=nombres, ExpressionAttributeValues=valores,
                                ReturnValues="ALL_NEW", **kw)["Attributes"]


# ------------------------------------------------------- acciones internas (Step Functions)
def iniciar(ev):
    op = ev["operacion"]
    fecha = iso(ahora())
    _tabla().put_item(Item={
        "id_operacion": op["id_operacion"], "fecha_inicio": fecha, "id_cliente": op["id_cliente"],
        "ejecucion_arn": ev.get("ejecucion"), "estado": EN_CURSO, "monto_origen": _ddb(op["monto_origen"]),
        "moneda_origen": op["moneda_origen"], "comprobante": op.get("comprobante_nombre")},
        ConditionExpression="attribute_not_exists(fecha_inicio)")
    log("validacion_iniciada", id_operacion=op["id_operacion"])
    return {"fecha_inicio": fecha}


def registrar_espera(ev):
    op = ev["operacion"]
    sets = {**_analisis(ev), "estado": EN_REVISION, "task_token": ev["token"], "fecha_revision": iso(ahora())}
    _actualizar(op["id_operacion"], ev["fecha_inicio"], sets)
    log("validacion_en_revision", id_operacion=op["id_operacion"])
    return {"ok": True}


def guardar(ev):
    op, dec = ev["operacion"], ev.get("decision") or {}
    fin = ahora()
    sets = {**_analisis(ev), "estado": FINALIZADA, "estado_final": ev.get("estado_final"),
            "decision": _ddb({**dec, "fecha": iso(fin)}), "fecha_fin": iso(fin)}
    _actualizar(op["id_operacion"], ev["fecha_inicio"], sets, quitar=("task_token",))
    log("validacion_finalizada", id_operacion=op["id_operacion"], decision=dec.get("decision"),
        decidido_por=dec.get("decidido_por"), estado_final=ev.get("estado_final"))
    return {"ok": True}


ACCIONES = {"iniciar": iniciar, "registrar_espera": registrar_espera, "guardar": guardar}


# --------------------------------------------------------------------------- rutas HTTP
def obtener_cliente(event):
    claims = exigir_sesion(event)
    v = _ultima(parametro_ruta(event, "id_operacion"))
    if not v or v["id_cliente"] != claims["sub"]:  # 404 (no 403) para no revelar existencia
        raise ApiError(404, "La operación no tiene validaciones registradas.", "sin_validacion")
    dec = v.get("decision") or {}
    return 200, {"id_operacion": v["id_operacion"], "estado": v["estado"], "fecha_inicio": v["fecha_inicio"],
                 "fecha_fin": v.get("fecha_fin"), "estado_final": v.get("estado_final"),
                 "decidido_por": dec.get("decidido_por"),
                 "motivo": dec.get("motivo") if dec.get("decision") == "rechazar" else None}


def obtener_admin(event):
    _exigir_admin(event)
    id_op = parametro_ruta(event, "id_operacion")
    items = _tabla().query(KeyConditionExpression=Key("id_operacion").eq(id_op), ScanIndexForward=False)["Items"]
    if not items:
        raise ApiError(404, "La operación no tiene validaciones registradas.", "sin_validacion")
    return 200, {"id_operacion": id_op, "validaciones": [_sin_token(i) for i in items], "total": len(items)}


def listar_admin(event):
    _exigir_admin(event)
    estado = ((event.get("queryStringParameters") or {}).get("estado") or EN_REVISION)
    if estado not in (EN_CURSO, EN_REVISION, FINALIZADA):
        raise ApiError(400, "Estado no válido.", "estado_invalido")
    kwargs = dict(IndexName="estado-fecha-index", KeyConditionExpression=Key("estado").eq(estado),
                  ScanIndexForward=estado != FINALIZADA)   # cola: más antigua primero; historial: reciente primero
    items = []
    while True:
        r = _tabla().query(**kwargs)
        items += r["Items"]
        if "LastEvaluatedKey" not in r or len(items) >= 200:
            break
        kwargs["ExclusiveStartKey"] = r["LastEvaluatedKey"]
    return 200, {"validaciones": [_sin_token(i) for i in items[:200]], "total": min(len(items), 200)}


def decidir(event):
    _exigir_admin(event)
    id_op = parametro_ruta(event, "id_operacion")
    d = cuerpo_json(event)
    decision = d.get("decision")
    if decision not in ("aprobar", "rechazar"):
        raise ApiError(400, "La decisión debe ser aprobar o rechazar.", "decision_invalida")
    motivo = texto(d.get("motivo", ""), "motivo", 3, 300) if decision == "rechazar" else None
    v = _ultima(id_op)
    if not v or v.get("estado") != EN_REVISION or not v.get("task_token"):
        raise ApiError(409, "Esta operación no está esperando una revisión.", "sin_revision_pendiente")
    # 1) quitar el token de forma condicional: si dos operadores deciden a la vez, solo uno gana
    try:
        _actualizar(id_op, v["fecha_inicio"], {"estado": EN_CURSO, "fecha_decision_operador": iso(ahora())},
                    quitar=("task_token",), condicion="#task_token = :tk", valores_extra={":tk": v["task_token"]})
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ApiError(409, "Otro operador ya decidió esta operación.", "ya_decidida")
        raise
    # 2) reanudar el workflow
    salida = {"decision": decision, "decidido_por": "operador", "motivo": motivo}
    try:
        _sfn().send_task_success(taskToken=v["task_token"], output=json.dumps(salida, ensure_ascii=False))
    except ClientError as e:
        codigo = e.response["Error"]["Code"]
        log("send_task_success_error", id_operacion=id_op, codigo=codigo)
        if codigo in ("TaskTimedOut", "TaskDoesNotExist", "InvalidToken"):
            raise ApiError(410, "La revisión venció; vuelve a consultar la operación.", "revision_vencida")
        # fallo transitorio: se devuelve el token para que el operador pueda reintentar
        _actualizar(id_op, v["fecha_inicio"], {"estado": EN_REVISION, "task_token": v["task_token"]})
        raise ApiError(502, "No pudimos registrar la decisión. Inténtalo nuevamente.", "servicio_no_disponible")
    log("decision_operador", id_operacion=id_op, decision=decision)
    return 202, {"mensaje": "Decisión registrada. La operación se actualizará en unos segundos.",
                 "id_operacion": id_op, "decision": decision}


def _detener_ejecuciones() -> int:
    """Detiene las ejecuciones de NexoGuard en curso (p. ej. revisiones que esperan un token)."""
    arn = os.environ.get("STATE_MACHINE_ARN")
    if not arn:
        return 0
    sfn, detenidas = _sfn(), 0
    for pagina in sfn.get_paginator("list_executions").paginate(stateMachineArn=arn, statusFilter="RUNNING"):
        for e in pagina["executions"]:
            sfn.stop_execution(executionArn=e["executionArn"], cause="Reinicio de datos de prueba")
            detenidas += 1
    return detenidas


def _vaciar_validaciones() -> int:
    tabla, borradas, kwargs = _tabla(), 0, {"ProjectionExpression": "id_operacion, fecha_inicio"}
    with tabla.batch_writer() as lote:
        while True:
            r = tabla.scan(**kwargs)
            for i in r["Items"]:
                lote.delete_item(Key={"id_operacion": i["id_operacion"], "fecha_inicio": i["fecha_inicio"]})
                borradas += 1
            if "LastEvaluatedKey" not in r:
                break
            kwargs["ExclusiveStartKey"] = r["LastEvaluatedKey"]
    return borradas


def _reiniciar_banco(conservar_demo: bool = True) -> dict:
    """El banco es un sistema externo: se reinicia por su propia API, con su propia clave."""
    url = os.environ.get("BANCO_API_URL", "").rstrip("/") + "/reiniciar"
    cuerpo = json.dumps({"conservar_demo": conservar_demo}).encode()
    req = urllib.request.Request(url, data=cuerpo, method="POST", headers={
        "x-banco-key": os.environ.get("BANCO_KEY", ""), "Content-Type": "application/json", "User-Agent": "nexoguard/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        log("banco_no_reiniciado", error=str(e)[:200])
        return {"error": "No se pudo reiniciar el banco simulado."}


def _reiniciar_operaciones() -> dict:
    """Operaciones es dueño de su tabla y sus comprobantes: se le pide por invocación interna."""
    r = boto3.client("lambda").invoke(FunctionName=os.environ["FN_OPERACIONES"], InvocationType="RequestResponse",
                                      Payload=json.dumps({"accion": "reiniciar_pruebas"}).encode())
    return json.loads(r["Payload"].read())


def reiniciar_demo(event):
    """Deja el entorno listo para repetir la demo con los mismos comprobantes (evita el «número ya usado»)."""
    _exigir_admin(event)
    d = cuerpo_json(event) if event.get("body") else {}
    res = {"ejecuciones_detenidas": _detener_ejecuciones(), "validaciones_borradas": _vaciar_validaciones(),
           "banco": _reiniciar_banco(d.get("conservar_demo", True) is not False)}
    if d.get("incluir_operaciones"):
        res["operaciones"] = _reiniciar_operaciones()
    log("demo_reiniciada", **{k: v for k, v in res.items() if not isinstance(v, dict)})
    return 200, {"mensaje": "Datos de prueba reiniciados.", **res}


_http = manejar({
    "GET /validaciones/admin": listar_admin,
    "GET /validaciones/{id_operacion}": obtener_cliente,
    "GET /validaciones/{id_operacion}/admin": obtener_admin,
    "POST /validaciones/{id_operacion}/decision": decidir,
    "POST /demo/reiniciar": reiniciar_demo,
})


def handler(event, context=None):
    accion = event.get("accion")
    if accion:  # invocación interna desde Step Functions: los errores se propagan para que el Retry/Catch actúe
        if accion not in ACCIONES:
            raise ValueError(f"Acción desconocida: {accion}")
        return ACCIONES[accion](event)
    return _http(event, context)

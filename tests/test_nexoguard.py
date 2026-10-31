"""NexoGuard: agentes, reglas, API Validaciones y cambios en Operaciones (Groq y Step Functions simulados)."""
import json
from datetime import date

import boto3
import pytest

from conftest import _cargar, cuerpo, evento
from test_operaciones import crear, hacer_cotizacion, sesion, subir

HOY = date.today().isoformat()
ADMIN = {"x-admin-key": "clave-admin-pruebas"}
OP = {"id_operacion": "NX-PRUEBA01", "id_cliente": "CLI-AAA", "modalidad": "casa", "moneda_origen": "PEN",
      "moneda_destino": "USD", "monto_origen": 1000.0, "monto_destino": 294.07, "tasa": 0.29407,
      "origen": {"tipo": "banco", "banco": "BCP"}, "destino": {"tipo": "banco", "banco": "Interbank"},
      "fecha_operacion": f"{HOY}T10:00:00.000Z", "ruta_comprobante": "s3://nexo-test-comprobantes/c/x.png",
      "comprobante_tipo": "image/png", "comprobante_nombre": "x.png"}


def leido(**kw):
    """Salida del Agente Extractor para el comprobante 01 (tomada de la prueba real con Groq)."""
    base = {"es_comprobante": True, "legible": True, "banco_origen": "BCP", "monto": 1000.0, "moneda": "PEN",
            "fecha": HOY, "hora": "10:15", "numero_operacion": "04417382", "destinatario": "NexoCambio S.A.C.",
            "cuenta_destino": "0-39", "banco_destino": "BCP", "confianza": 0.95, "observaciones": ""}
    return {**base, **kw}


@pytest.fixture
def ver():
    return _cargar("guard_verificar")


@pytest.fixture
def rie(monkeypatch):
    m = _cargar("guard_riesgo")
    m.respuesta_ia = {"semaforo": "verde", "justificacion": "Todo coincide.", "motivo_rechazo": None}
    monkeypatch.setattr(m, "chat_json", lambda modelo, prompt: m.respuesta_ia)
    return m


@pytest.fixture
def val(monkeypatch):
    m = _cargar("validaciones")
    m.tokens = []

    class SfnFalso:
        def send_task_success(self, taskToken, output):
            m.tokens.append((taskToken, json.loads(output)))

    monkeypatch.setattr(m, "_sfn", lambda: SfnFalso())
    return m


# --------------------------------------------------------------------------- reglas
def resultados(res):
    return {r["regla"]: r["resultado"] for r in res["reglas"]}


def test_verificar_comprobante_correcto(ver):
    res = ver.verificar(OP, leido())
    assert res["todo_cumple"] and res["lectura_confiable"] and not res["discrepancias_duras"]
    assert set(resultados(res).values()) == {"cumple"}


def test_verificar_cci_interbancario_de_nexocambio(ver):
    res = ver.verificar(OP, leido(banco_origen="Interbank", cuenta_destino="CCI ****0039-14", monto=1000))
    assert resultados(res)["cuenta_destino"] == "cumple" and resultados(res)["banco_origen"] == "no_cumple"
    assert res["todo_cumple"]          # el banco de origen solo es informativo


@pytest.mark.parametrize("cambio, regla", [
    ({"monto": 850.0}, "monto"),
    ({"moneda": "USD"}, "moneda"),
    ({"destinatario": "Inversiones Andinas E.I.R.L.", "cuenta_destino": "7716"}, "cuenta_destino"),
])
def test_verificar_discrepancias_duras(ver, cambio, regla):
    res = ver.verificar(OP, leido(**cambio))
    assert resultados(res)[regla] == "no_cumple" and len(res["discrepancias_duras"]) == 1


def test_verificar_detecta_comprobante_duplicado(ver):
    boto3.resource("dynamodb").Table("nexo-test-validaciones").put_item(Item={
        "id_operacion": "NX-OTRA", "fecha_inicio": "2026-11-01T00:00:00.000Z", "estado": "finalizada",
        "numero_operacion": "04417382"})
    res = ver.verificar(OP, leido())
    assert resultados(res)["numero_operacion_unico"] == "no_cumple"
    assert "NX-OTRA" in res["discrepancias_duras"][0]


def test_verificar_lectura_no_confiable_no_rechaza(ver):
    res = ver.verificar(OP, leido(legible=False, confianza=0.35, monto=500.0, numero_operacion=None))
    assert not res["lectura_confiable"] and res["discrepancias_duras"] == []   # va a revisión, no a rechazo
    assert res["motivos_revision"]


def test_verificar_fecha_anterior_a_la_operacion(ver):
    res = ver.verificar(OP, leido(fecha="2025-01-01"))
    assert resultados(res)["fecha"] == "no_cumple" and not res["discrepancias_duras"] and not res["todo_cumple"]


# --------------------------------------------------------------------------- riesgo
def test_riesgo_verde_aprueba(ver, rie):
    r = rie.evaluar(OP, leido(), ver.verificar(OP, leido()))
    assert (r["semaforo"], r["ruta"], r["alerta_cumplimiento"]) == ("verde", "aprobar", False)
    assert r["monto_usd"] == 294.07


def test_riesgo_agente_no_puede_bajar_ni_rechazar_sin_reglas(ver, rie):
    v = ver.verificar(OP, leido(fecha="2025-01-01"))            # mínimo amarillo
    assert rie.evaluar(OP, leido(), v)["ruta"] == "revision"    # el agente dice verde: no baja
    rie.respuesta_ia = {"semaforo": "rojo", "justificacion": "Sospechoso.", "motivo_rechazo": "x"}
    r = rie.evaluar(OP, leido(), ver.verificar(OP, leido()))
    assert (r["semaforo"], r["ruta"]) == ("amarillo", "revision")   # sin discrepancia dura no rechaza


def test_riesgo_discrepancia_dura_rechaza_con_motivo_de_la_regla(ver, rie):
    r = rie.evaluar(OP, leido(monto=850.0), ver.verificar(OP, leido(monto=850.0)))
    assert (r["semaforo"], r["ruta"]) == ("rojo", "rechazar")
    assert "850.00" in r["motivo_rechazo"]


def test_riesgo_monto_alto_alerta_cumplimiento(ver, rie):
    op = {**OP, "moneda_origen": "USD", "moneda_destino": "PEN", "monto_origen": 12000.0, "monto_destino": 40800.0}
    ex = leido(moneda="USD", monto=12000.0, cuenta_destino="****1147-17")
    r = rie.evaluar(op, ex, ver.verificar(op, ex))
    assert (r["semaforo"], r["ruta"], r["alerta_cumplimiento"]) == ("amarillo", "revision", True)


# --------------------------------------------------------------------------- extractor
def test_extractor_normaliza_y_rechaza_pdf(monkeypatch):
    ext = _cargar("guard_extraer")
    n = ext.normalizar({"es_comprobante": True, "legible": True, "banco_origen": "SCOTIABANK", "monto": "12,000.00",
                        "moneda": "usd", "numero_operacion": "N° 900-344", "confianza": 1.4})
    assert (n["banco_origen"], n["monto"], n["moneda"], n["numero_operacion"], n["confianza"]) == \
        ("Scotiabank", 12000.0, "USD", "900344", 1.0)
    pdf = ext.handler({"operacion": {**OP, "comprobante_tipo": "application/pdf"}})
    assert pdf["legible"] is False and "PDF" in pdf["observaciones"]

    boto3.client("s3").put_object(Bucket="nexo-test-comprobantes", Key="c/x.png", Body=b"\x89PNG\r\n\x1a\nfalso")
    llamadas = []
    monkeypatch.setattr(ext, "chat_json", lambda modelo, contenido: llamadas.append(contenido) or leido())
    res = ext.handler({"operacion": OP})
    assert res["monto"] == 1000.0 and res["modelo"] == "modelo-vision"
    assert llamadas[0][1]["image_url"]["url"].startswith("data:image/png;base64,")


# --------------------------------------------------------------------------- API Validaciones
def test_validaciones_flujo_revision_humana(val):
    ini = val.handler({"accion": "iniciar", "operacion": OP, "ejecucion": "arn:exec"})
    analisis = {"operacion": OP, "fecha_inicio": ini["fecha_inicio"], "extraccion": leido(),
                "verificacion": {"reglas": []}, "riesgo": {"semaforo": "amarillo", "ruta": "revision",
                                                          "justificacion": "Monto alto.", "monto_usd": 294.07}}
    val.handler({"accion": "registrar_espera", "token": "TOKEN-1", **analisis})

    cola = cuerpo(val.handler({**evento("GET /validaciones/admin", headers=ADMIN), "queryStringParameters": None}))
    assert cola["total"] == 1 and cola["validaciones"][0]["semaforo"] == "amarillo"
    assert "task_token" not in cola["validaciones"][0]          # el token nunca sale de la API

    p = {"id_operacion": OP["id_operacion"]}
    r = val.handler(evento("POST /validaciones/{id_operacion}/decision", {"decision": "rechazar"}, params=p, headers=ADMIN))
    assert r["statusCode"] == 400                                # rechazar exige motivo
    r = val.handler(evento("POST /validaciones/{id_operacion}/decision",
                           {"decision": "rechazar", "motivo": "Comprobante alterado."}, params=p, headers=ADMIN))
    assert r["statusCode"] == 202
    assert val.tokens == [("TOKEN-1", {"decision": "rechazar", "decidido_por": "operador", "motivo": "Comprobante alterado."})]
    r = val.handler(evento("POST /validaciones/{id_operacion}/decision", {"decision": "aprobar"}, params=p, headers=ADMIN))
    assert r["statusCode"] == 409                                # ya no espera revisión

    val.handler({"accion": "guardar", **analisis, "estado_final": "Rechazada",
                 "decision": {"decision": "rechazar", "decidido_por": "operador", "motivo": "Comprobante alterado."}})
    det = cuerpo(val.handler(evento("GET /validaciones/{id_operacion}/admin", params=p, headers=ADMIN)))
    v = det["validaciones"][0]
    assert v["estado"] == "finalizada" and v["numero_operacion"] == "04417382" and "task_token" not in v


def test_validaciones_vista_cliente_y_aislamiento(val, cli):
    tk = sesion(cli)
    import nexo_common as nc
    sub = nc.jwt_validar(tk, "secreto-de-pruebas-0123456789")["sub"]
    val.handler({"accion": "iniciar", "operacion": {**OP, "id_cliente": sub}})
    p = {"id_operacion": OP["id_operacion"]}
    r = cuerpo(val.handler(evento("GET /validaciones/{id_operacion}", token=tk, params=p)))
    assert r["estado"] == "en_curso" and "justificacion" not in r
    otro = nc.jwt_crear({"sub": "CLI-OTRO"}, "secreto-de-pruebas-0123456789")
    assert val.handler(evento("GET /validaciones/{id_operacion}", token=otro, params=p))["statusCode"] == 404
    assert val.handler(evento("GET /validaciones/admin"))["statusCode"] == 403


# --------------------------------------------------------------------------- Operaciones
def test_comprobante_inicia_nexoguard_y_aplicar_decision(cli, cot, ops, monkeypatch):
    iniciadas = []

    class SfnFalso:
        def start_execution(self, **kw):
            iniciadas.append(kw)

    real = ops.boto3.client
    monkeypatch.setattr(ops.boto3, "client", lambda svc, **kw: SfnFalso() if svc == "stepfunctions" else real(svc, **kw))
    monkeypatch.setenv("STATE_MACHINE_ARN", "arn:aws:states:us-east-1:123:stateMachine:nexo-test-nexoguard")
    tk = sesion(cli)
    op = cuerpo(crear(ops, tk, hacer_cotizacion(cot)))
    assert subir(ops, tk, op["id_operacion"])["statusCode"] == 200
    entrada = json.loads(iniciadas[0]["input"])["operacion"]
    assert iniciadas[0]["name"].startswith(op["id_operacion"] + "-")
    assert entrada["monto_origen"] == 1000 and entrada["ruta_comprobante"].startswith("s3://")

    r = ops.handler({"accion": "aplicar_decision", "id_operacion": op["id_operacion"], "decision": "aprobar",
                     "decidido_por": "agente"})
    assert r == {"ok": True, "aplicado": True, "estado": "En proceso"}
    det = cuerpo(ops.handler(evento("GET /operaciones/{id_operacion}", token=tk, params={"id_operacion": op["id_operacion"]})))
    assert det["historial"][-1]["actor"] == "agente" and det["estado"] == "En proceso"
    # una segunda decisión (p. ej. de una validación antigua) no cambia nada
    r = ops.handler({"accion": "aplicar_decision", "id_operacion": op["id_operacion"], "decision": "rechazar"})
    assert r == {"ok": True, "aplicado": False, "estado": "En proceso"}


def test_comprobante_no_falla_si_step_functions_no_responde(cli, cot, ops, monkeypatch):
    monkeypatch.setenv("STATE_MACHINE_ARN", "arn:aws:states:us-east-1:123:stateMachine:no-existe")
    tk = sesion(cli)
    op = cuerpo(crear(ops, tk, hacer_cotizacion(cot)))
    r = subir(ops, tk, op["id_operacion"])
    assert r["statusCode"] == 200 and cuerpo(r)["estado"] == "Pendiente de validación"

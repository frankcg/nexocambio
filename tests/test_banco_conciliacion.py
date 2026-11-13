"""Banco simulado, conciliación (ConciliarConBanco), su efecto en el riesgo y el reinicio de datos de prueba."""
import json
from datetime import date

import boto3
import pytest

from conftest import _cargar, cuerpo, evento
from test_nexoguard import OP, leido

BANCO = {"x-banco-key": "clave-banco-pruebas"}
ADMIN = {"x-admin-key": "clave-admin-pruebas"}
HOY = date.today().isoformat()


@pytest.fixture
def banco():
    return _cargar("banco_simulado")


@pytest.fixture
def conc(banco, monkeypatch):
    """guard-conciliar con la llamada HTTP al banco redirigida al handler del banco simulado (mismo contrato)."""
    m = _cargar("guard_conciliar")

    def consultar(**params):
        r = banco.handler({**evento("GET /banco/depositos", headers=BANCO), "queryStringParameters": params})
        assert r["statusCode"] == 200
        return cuerpo(r)["depositos"]

    monkeypatch.setattr(m, "_consultar", consultar)
    return m


def depositar(banco, **kw):
    base = {"cuenta_destino": "**** 0-39", "monto": 1000, "moneda": "PEN", "numero_operacion": "04417382",
            "banco_origen": "BCP", "ordenante": "Lucía Ramírez"}
    return banco.handler(evento("POST /banco/depositos", {**base, **kw}, headers=BANCO))


# --------------------------------------------------------------------------- banco simulado
def test_banco_exige_su_propia_clave(banco):
    assert depositar(banco)["statusCode"] == 201
    r = banco.handler(evento("POST /banco/depositos", {"monto": 1}, headers=ADMIN))   # la clave del back-office no sirve
    assert r["statusCode"] == 403


def test_banco_registra_y_consulta_depositos(banco):
    r = depositar(banco, cuenta_destino="CCI ****0039-14")      # el CCI se traduce a la cuenta de NexoCambio
    assert r["statusCode"] == 201 and cuerpo(r)["cuenta"] == "1932458710039"
    assert depositar(banco, cuenta_destino="CCI ****0039-14")["statusCode"] == 409
    assert depositar(banco, cuenta_destino="7716", numero_operacion="1")["statusCode"] == 422
    q = banco.handler({**evento("GET /banco/depositos", headers=BANCO), "queryStringParameters": {"numero_operacion": "04417382"}})
    assert cuerpo(q)["total"] == 1 and cuerpo(q)["depositos"][0]["monto"] == 1000


def test_banco_reiniciar_borra_pruebas_y_carga_semilla(banco):
    depositar(banco)
    r = cuerpo(banco.handler(evento("POST /banco/reiniciar", {}, headers=BANCO)))
    assert r == {"borrados": 1, "conservados": 0, "semilla": 20}
    items = boto3.resource("dynamodb").Table("nexo-test-banco").scan()["Items"]
    assert len(items) == 20 and {i["origen_datos"] for i in items} == {"semilla"}


def test_banco_reiniciar_conserva_los_depositos_de_la_demo(banco):
    depositar(banco, origen_datos="demo")                      # comprobante de la demo web
    depositar(banco, numero_operacion="05550001")              # depósito de una prueba (Postman, E2E)
    r = cuerpo(banco.handler(evento("POST /banco/reiniciar", {}, headers=BANCO)))
    assert (r["borrados"], r["conservados"]) == (1, 1)
    q = banco.handler({**evento("GET /banco/depositos", headers=BANCO), "queryStringParameters": {"numero_operacion": "04417382"}})
    assert cuerpo(q)["total"] == 1                             # el caso verde de la demo sigue teniendo su depósito
    r = cuerpo(banco.handler(evento("POST /banco/reiniciar", {"conservar_demo": False}, headers=BANCO)))
    assert (r["borrados"], r["conservados"]) == (21, 0)        # preparar_exposicion.py: borra la demo y la semilla


# --------------------------------------------------------------------------- conciliación
def test_conciliacion_total(conc, banco):
    depositar(banco)
    r = conc.handler({"operacion": OP, "extraccion": leido(), "intento": 0})
    assert (r["coincidencia"], r["encontrado"], r["intento"]) == ("total", True, 1)
    assert r["max_intentos"] == 4 and r["espera_seg"] == 30


def test_conciliacion_parcial_por_monto(conc, banco):
    depositar(banco, monto=850)
    r = conc.handler({"operacion": OP, "extraccion": leido(monto=850.0), "intento": 0})
    assert (r["coincidencia"], r["encontrado"]) == ("parcial", True) and "850.00" in r["detalle"]


def test_conciliacion_sin_numero_busca_por_monto_y_fecha(conc, banco):
    depositar(banco, fecha=HOY)
    r = conc.handler({"operacion": OP, "extraccion": leido(numero_operacion=None, fecha=HOY), "intento": 2})
    assert (r["coincidencia"], r["intento"]) == ("parcial", 3)


def test_conciliacion_comprobante_sin_deposito(conc, banco):
    banco.handler(evento("POST /banco/reiniciar", {}, headers=BANCO))      # solo datos semilla
    r = conc.handler({"operacion": OP, "extraccion": leido(numero_operacion="55555555"), "intento": 0})
    assert (r["coincidencia"], r["encontrado"]) == ("ninguna", False) and "55555555" in r["detalle"]


# --------------------------------------------------------------------------- efecto en el riesgo
@pytest.fixture
def rie(monkeypatch):
    m = _cargar("guard_riesgo")
    monkeypatch.setattr(m, "chat_json", lambda modelo, prompt, **kw: {"semaforo": "verde", "justificacion": "Ok."})
    return m


@pytest.mark.parametrize("coincidencia, semaforo", [("total", "verde"), ("parcial", "amarillo"),
                                                    ("ninguna", "amarillo"), ("error", "amarillo")])
def test_riesgo_con_conciliacion(rie, coincidencia, semaforo):
    ver = {"reglas": [], "lectura_confiable": True, "discrepancias_duras": [], "motivos_revision": [], "todo_cumple": True}
    r = rie.evaluar(OP, leido(), ver, {"coincidencia": coincidencia, "detalle": "Detalle del banco.", "intento": 4})
    assert r["semaforo"] == semaforo and r["verificaciones"][-1]["regla"] == "deposito_banco"
    if coincidencia == "ninguna":
        assert "tras 4 consulta(s) al banco" in r["justificacion"]


# --------------------------------------------------------------------------- reinicio de datos de prueba
def test_reiniciar_demo(monkeypatch):
    val = _cargar("validaciones")
    boto3.resource("dynamodb").Table("nexo-test-validaciones").put_item(Item={
        "id_operacion": "NX-1", "fecha_inicio": "2026-11-01T00:00:00.000Z", "estado": "en_revision", "numero_operacion": "1"})
    detenidas = []

    class SfnFalso:
        def get_paginator(self, _):
            return type("P", (), {"paginate": lambda self, **kw: [{"executions": [{"executionArn": "arn:exec:1"}]}]})()

        def stop_execution(self, executionArn, cause):
            detenidas.append(executionArn)

    monkeypatch.setenv("STATE_MACHINE_ARN", "arn:aws:states:us-east-1:1:stateMachine:x")
    monkeypatch.setattr(val, "_sfn", lambda: SfnFalso())
    pedidos = []
    monkeypatch.setattr(val, "_reiniciar_banco", lambda conservar_demo=True: pedidos.append(conservar_demo) or {"borrados": 3, "semilla": 20})
    monkeypatch.setattr(val, "_reiniciar_operaciones", lambda: {"operaciones_borradas": 2})

    assert val.handler(evento("POST /demo/reiniciar", {}))["statusCode"] == 403
    r = cuerpo(val.handler(evento("POST /demo/reiniciar", {"incluir_operaciones": True}, headers=ADMIN)))
    assert r["ejecuciones_detenidas"] == 1 and r["validaciones_borradas"] == 1 and detenidas == ["arn:exec:1"]
    assert r["banco"]["semilla"] == 20 and r["operaciones"]["operaciones_borradas"] == 2
    assert boto3.resource("dynamodb").Table("nexo-test-validaciones").scan()["Count"] == 0
    val.handler(evento("POST /demo/reiniciar", {"conservar_demo": False}, headers=ADMIN))
    assert pedidos == [True, False]                            # por defecto conserva los depósitos de la demo


def test_operaciones_reiniciar_pruebas(cli, cot, ops):
    from test_operaciones import crear, hacer_cotizacion, sesion, subir
    tk = sesion(cli)
    op = cuerpo(crear(ops, tk, hacer_cotizacion(cot)))
    subir(ops, tk, op["id_operacion"])
    r = ops.handler({"accion": "reiniciar_pruebas"})
    assert r == {"operaciones_borradas": 1, "comprobantes_borrados": 1}
    assert cuerpo(ops.handler(evento("GET /operaciones", token=tk)))["total"] == 0

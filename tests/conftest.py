"""Fixtures: AWS simulado con moto (DynamoDB + S3). No requiere credenciales ni internet."""
import importlib.util
import json
import os
import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "layer" / "python"))

ENTORNO = {
    "AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test", "AWS_DEFAULT_REGION": "us-east-1",
    "TABLE_CLIENTES": "nexo-test-clientes", "TABLE_COTIZACIONES": "nexo-test-cotizaciones",
    "TABLE_TASAS": "nexo-test-tasas", "TABLE_OPERACIONES": "nexo-test-operaciones",
    "BUCKET_COMPROBANTES": "nexo-test-comprobantes", "FN_COTIZACIONES": "nexo-test-cotizaciones",
    "JWT_SECRET": "secreto-de-pruebas-0123456789", "ADMIN_KEY": "clave-admin-pruebas",
    "PBKDF2_ITER": "1000", "USAR_TASAS_EN_VIVO": "false",
}


def _cargar(nombre):
    spec = importlib.util.spec_from_file_location(f"app_{nombre}", RAIZ / "services" / nombre / "app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def aws(monkeypatch):
    for k, v in ENTORNO.items():
        monkeypatch.setenv(k, v)
    with mock_aws():
        db = boto3.client("dynamodb")
        db.create_table(TableName="nexo-test-clientes", BillingMode="PAY_PER_REQUEST",
                        AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
                        KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}])
        db.create_table(TableName="nexo-test-cotizaciones", BillingMode="PAY_PER_REQUEST",
                        AttributeDefinitions=[{"AttributeName": "id_cotizacion", "AttributeType": "S"}],
                        KeySchema=[{"AttributeName": "id_cotizacion", "KeyType": "HASH"}])
        db.create_table(TableName="nexo-test-tasas", BillingMode="PAY_PER_REQUEST",
                        AttributeDefinitions=[{"AttributeName": "moneda", "AttributeType": "S"}],
                        KeySchema=[{"AttributeName": "moneda", "KeyType": "HASH"}])
        db.create_table(TableName="nexo-test-operaciones", BillingMode="PAY_PER_REQUEST",
                        AttributeDefinitions=[{"AttributeName": "id_operacion", "AttributeType": "S"},
                                              {"AttributeName": "id_cliente", "AttributeType": "S"},
                                              {"AttributeName": "fecha_operacion", "AttributeType": "S"}],
                        KeySchema=[{"AttributeName": "id_operacion", "KeyType": "HASH"}],
                        GlobalSecondaryIndexes=[{"IndexName": "cliente-fecha-index",
                                                 "KeySchema": [{"AttributeName": "id_cliente", "KeyType": "HASH"},
                                                               {"AttributeName": "fecha_operacion", "KeyType": "RANGE"}],
                                                 "Projection": {"ProjectionType": "ALL"}}])
        boto3.client("s3").create_bucket(Bucket="nexo-test-comprobantes")
        yield


@pytest.fixture
def cot():
    return _cargar("cotizaciones")


@pytest.fixture
def cli():
    return _cargar("clientes")


@pytest.fixture
def ops(cot):
    m = _cargar("operaciones")

    def via_lambda(id_cotizacion):  # simula Lambda→Lambda con el mismo formato JSON
        from nexo_common import ApiError
        r = cot.handler({"accion": "obtener", "id_cotizacion": id_cotizacion})
        if not r["ok"]:
            raise ApiError(404, r["mensaje"], "cotizacion_no_encontrada")
        return r["cotizacion"]

    m.cotizaciones_obtener = via_lambda
    return m


def evento(ruta, cuerpo=None, token=None, params=None, headers=None):
    h = {"content-type": "application/json", **(headers or {})}
    if token:
        h["authorization"] = f"Bearer {token}"
    return {"routeKey": ruta, "headers": h, "pathParameters": params or {},
            "body": json.dumps(cuerpo) if cuerpo is not None else None, "isBase64Encoded": False}


def cuerpo(resp):
    return json.loads(resp["body"])


PERSONA = {"tipo_cliente": "persona", "nombres": "Lucía", "apellidos": "Ramírez Torres", "tipo_documento": "DNI",
           "numero_documento": "45879632", "fecha_nacimiento": "1994-05-10", "telefono": "987654321",
           "ocupacion": "Dependiente", "pep": False, "correo": "lucia@correo.com", "password": "Clave1234"}
EMPRESA = {"tipo_cliente": "empresa", "razon_social": "Importaciones Andina SAC", "tipo_documento": "RUC",
           "numero_documento": "20601234567", "actividad": "Comercio", "telefono": "912345678",
           "correo": "finanzas@andina.pe", "password": "Empresa2026",
           "representante": {"nombre": "Carlos Quispe Rojas", "tipo_documento": "DNI",
                             "numero_documento": "40123456", "cargo": "Gerente general"}}
PNG_1X1 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")

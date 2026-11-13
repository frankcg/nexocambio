"""
BANCO SIMULADO  (AWS Lambda · Python 3.12) — sistema EXTERNO a NexoCambio

Simula la API de movimientos de un banco (en producción: la API corporativa del BCP, Interbank…
o un agregador como Prometeo). Registra los DEPÓSITOS que llegan a las cuentas de NexoCambio
cuando un cliente transfiere, y permite consultarlos para la conciliación de NexoGuard.

No comparte nada con NexoCambio: su propia tabla, sus propias rutas y su propia clave
(cabecera x-banco-key). NexoGuard la consume por HTTPS, como consumiría la API de un banco real.

Base de datos propia: DynamoDB nexo-<stage>-banco-movimientos
    PK cuenta (número de cuenta de NexoCambio, solo dígitos) · SK mov (<fecha>#<numero_operacion>)
    GSI numero-operacion-index (numero_operacion)

Rutas (todas con x-banco-key):
  POST /banco/depositos     registra un depósito ("el cliente transfirió")       → 201 · 409 si ya existe
  GET  /banco/depositos     ?numero_operacion=…  |  ?cuenta=…&fecha=AAAA-MM-DD   → {depositos}
  POST /banco/reiniciar     {conservar_demo?} borra los depósitos de prueba y recarga los datos semilla.
                            Conserva los de la demo web (origen_datos "demo") salvo conservar_demo: false
"""
import hmac
import os
from datetime import timedelta
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

import nexo_cuentas
from nexo_common import ApiError, ahora, cuerpo_json, encabezado, iso, log, manejar, texto

MONEDAS = {"PEN", "USD", "EUR"}

# Depósitos "históricos" de otros clientes: hacen que la búsqueda no sea trivial
SEMILLA = [  # (días atrás, moneda, banco NexoCambio, monto, banco origen, ordenante, número)
    (1, "PEN", "BCP", "350.00", "BCP", "María Quispe", "90100001"),
    (1, "PEN", "BCP", "1200.00", "Interbank", "Jorge Salas", "90100002"),
    (1, "USD", "BCP", "500.00", "BBVA", "Andina Import SAC", "90100003"),
    (2, "PEN", "Interbank", "800.00", "Interbank", "Rosa Huamán", "90100004"),
    (2, "PEN", "BCP", "2500.00", "Scotiabank", "Luis Paredes", "90100005"),
    (2, "USD", "Interbank", "1500.00", "Interbank", "Textiles Lima SAC", "90100006"),
    (3, "PEN", "BBVA", "640.00", "BBVA", "Carla Ríos", "90100007"),
    (3, "PEN", "BCP", "1000.00", "BCP", "Diego Torres", "90100008"),
    (3, "USD", "BCP", "300.00", "BCP", "Ana Vargas", "90100009"),
    (4, "PEN", "Scotiabank", "4300.00", "Scotiabank", "Agroexport Norte SAC", "90100010"),
    (4, "PEN", "BCP", "150.00", "Interbank", "Pedro Flores", "90100011"),
    (4, "USD", "BBVA", "2000.00", "BBVA", "Minera Sur SAC", "90100012"),
    (5, "PEN", "Interbank", "720.00", "BCP", "Lucía Mendoza", "90100013"),
    (5, "PEN", "BCP", "980.00", "BBVA", "Raúl Castro", "90100014"),
    (5, "EUR", "BCP", "400.00", "BCP", "Elena Gómez", "90100015"),
    (6, "PEN", "BCP", "5000.00", "BCP", "Constructora Andes SAC", "90100016"),
    (6, "USD", "Scotiabank", "750.00", "Scotiabank", "Mario León", "90100017"),
    (7, "PEN", "BBVA", "260.00", "Interbank", "Sofía Chávez", "90100018"),
    (7, "PEN", "BCP", "1800.00", "BCP", "Inversiones Pacífico SAC", "90100019"),
    (7, "USD", "BCP", "100.00", "Interbank", "Hugo Rojas", "90100020"),
]


def _tabla():
    return boto3.resource("dynamodb").Table(os.environ["TABLE_BANCO"])


def _exigir_clave(event) -> None:
    clave_esperada = os.environ.get("BANCO_KEY", "")
    clave = encabezado(event, "x-banco-key") or ""
    if not clave_esperada or not hmac.compare_digest(clave, clave_esperada):
        raise ApiError(403, "Credenciales del banco inválidas.", "prohibido")


def _item(cuenta, fecha, numero, monto, moneda, banco_origen, ordenante, origen_datos):
    return {"cuenta": cuenta, "mov": f"{fecha}#{numero}", "fecha": fecha, "numero_operacion": numero,
            "monto": Decimal(str(monto)), "moneda": moneda, "banco_origen": banco_origen, "ordenante": ordenante,
            "origen_datos": origen_datos, "registrado": iso(ahora())}


def registrar(event):
    _exigir_clave(event)
    d = cuerpo_json(event)
    moneda = str(d.get("moneda", "")).upper()
    if moneda not in MONEDAS:
        raise ApiError(422, "Moneda no válida.", "moneda_invalida")
    cuenta = nexo_cuentas.cuenta_de(d.get("cuenta_destino"), moneda)
    if not cuenta:
        raise ApiError(422, "La cuenta de destino no es una cuenta de NexoCambio en esa moneda.", "cuenta_invalida")
    numero = nexo_cuentas.digitos(d.get("numero_operacion"))
    if not 4 <= len(numero) <= 20:
        raise ApiError(422, "El número de operación debe tener entre 4 y 20 dígitos.", "numero_invalido")
    try:
        monto = Decimal(str(d.get("monto")))
        assert monto > 0
    except Exception:  # noqa: BLE001
        raise ApiError(422, "El monto debe ser mayor a cero.", "monto_invalido")
    fecha = str(d.get("fecha") or ahora().date().isoformat())[:10]
    item = _item(cuenta, fecha, numero, monto, moneda, texto(str(d.get("banco_origen") or "BCP"), "banco_origen", 2, 40),
                 texto(str(d.get("ordenante") or "Cliente"), "ordenante", 2, 120), d.get("origen_datos") or "prueba")
    try:
        _tabla().put_item(Item=item, ConditionExpression="attribute_not_exists(mov)")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ApiError(409, "Ese depósito ya está registrado.", "duplicado")
        raise
    log("deposito_registrado", cuenta=cuenta, numero=numero, monto=str(monto), moneda=moneda)
    return 201, item


def consultar(event):
    _exigir_clave(event)
    q = event.get("queryStringParameters") or {}
    numero = nexo_cuentas.digitos(q.get("numero_operacion"))
    if numero:
        items = _tabla().query(IndexName="numero-operacion-index",
                               KeyConditionExpression=Key("numero_operacion").eq(numero))["Items"]
    elif q.get("cuenta") and q.get("fecha"):
        r = _tabla().query(KeyConditionExpression=Key("cuenta").eq(nexo_cuentas.digitos(q["cuenta"]))
                           & Key("mov").begins_with(str(q["fecha"])[:10]))
        items = r["Items"]
    else:
        raise ApiError(400, "Indica numero_operacion, o cuenta y fecha.", "parametros_faltantes")
    return 200, {"depositos": items, "total": len(items)}


def reiniciar(event):
    _exigir_clave(event)
    conservar_demo = (cuerpo_json(event) if event.get("body") else {}).get("conservar_demo", True) is not False
    tabla = _tabla()
    borrados, conservados, kwargs = 0, 0, {"ProjectionExpression": "cuenta, mov, origen_datos"}
    with tabla.batch_writer() as lote:
        while True:
            r = tabla.scan(**kwargs)
            for i in r["Items"]:
                if conservar_demo and i.get("origen_datos") == "demo":   # los comprobantes de la demo web siguen válidos
                    conservados += 1
                    continue
                lote.delete_item(Key={"cuenta": i["cuenta"], "mov": i["mov"]})
                borrados += 1
            if "LastEvaluatedKey" not in r:
                break
            kwargs["ExclusiveStartKey"] = r["LastEvaluatedKey"]
    hoy = ahora().date()
    with tabla.batch_writer() as lote:
        for dias, moneda, banco, monto, banco_origen, ordenante, numero in SEMILLA:
            cuenta = nexo_cuentas.digitos(nexo_cuentas.CUENTAS[moneda][banco][0])
            lote.put_item(Item=_item(cuenta, (hoy - timedelta(days=dias)).isoformat(), numero, monto, moneda,
                                     banco_origen, ordenante, "semilla"))
    log("banco_reiniciado", borrados=borrados, conservados=conservados, semilla=len(SEMILLA))
    return 200, {"borrados": borrados, "conservados": conservados, "semilla": len(SEMILLA)}


handler = manejar({
    "POST /banco/depositos": registrar,
    "GET /banco/depositos": consultar,
    "POST /banco/reiniciar": reiniciar,
})

"""
Microservicio 2 — CLIENTES Y AUTENTICACIÓN  (AWS Lambda · Python 3.12)

Responsabilidad: registro de clientes (persona natural / empresa), inicio de
sesión (JWT HS256) y consulta del perfil básico.

Base de datos propia (Amazon DynamoDB): nexo-<stage>-clientes, clave `pk`
(diseño de una sola tabla con ítems de unicidad):

  pk = CLI#<id_cliente>            perfil completo (incluye password_hash)
  pk = EMAIL#<correo>              → id_cliente   (garantiza correo único)
  pk = DOC#<tipo>#<numero>         → id_cliente   (garantiza documento único)

El registro escribe los 3 ítems en UNA transacción con
`attribute_not_exists(pk)`, por lo que no puede haber duplicados aunque dos
solicitudes lleguen a la vez.

Rutas HTTP:
  POST /registro              (pública)
  POST /login                 (pública)
  GET  /clientes/{id_cliente} (requiere JWT; solo el propio cliente)
"""
import os
from datetime import date

import boto3
from botocore.exceptions import ClientError

from nexo_common import (ApiError, ahora, cuerpo_json, encabezado, exigir_sesion,
                         hash_password, iso, jwt_crear, log, manejar, nuevo_id,
                         parametro_ruta, requeridos, texto, validar_documento,
                         validar_password, verificar_password, RE_CELULAR,
                         RE_CORREO)

OCUPACIONES = {"Dependiente", "Independiente", "Empresario", "Estudiante", "Jubilado", "Otro"}
ACTIVIDADES = {"Comercio", "Servicios", "Manufactura", "Tecnología", "Construcción", "Otro"}
DOC_PERSONA = {"DNI", "CE", "Pasaporte"}


def _tabla():
    return boto3.resource("dynamodb").Table(os.environ["TABLE_CLIENTES"])


def _edad(fecha_iso: str) -> int:
    try:
        f = date.fromisoformat(fecha_iso)
    except Exception:  # noqa: BLE001
        raise ApiError(400, "La fecha de nacimiento debe tener el formato AAAA-MM-DD.", "fecha_invalida")
    hoy = date.today()
    return hoy.year - f.year - ((hoy.month, hoy.day) < (f.month, f.day))


def _perfil_publico(c: dict) -> dict:
    ocultos = {"pk", "password_hash"}
    return {k: v for k, v in c.items() if k not in ocultos}


# ------------------------------------------------------------------ registro
def _validar_registro(d: dict) -> dict:
    tipo = d.get("tipo_cliente")
    if tipo not in ("persona", "empresa"):
        raise ApiError(400, "tipo_cliente debe ser 'persona' o 'empresa'.", "tipo_cliente_invalido")
    requeridos(d, ["tipo_documento", "numero_documento", "telefono", "correo", "password"])
    correo = texto(d["correo"], "correo", 5, 120).lower()
    if not RE_CORREO.match(correo):
        raise ApiError(400, "Ingresa un correo válido, por ejemplo nombre@correo.com.", "correo_invalido")
    if not RE_CELULAR.match(str(d["telefono"])):
        raise ApiError(400, "El celular debe tener 9 dígitos y empezar con 9.", "telefono_invalido")
    validar_password(d["password"])
    numero = texto(str(d["numero_documento"]), "numero_documento", 1, 20)

    base = {"tipo_cliente": tipo, "correo": correo, "telefono": str(d["telefono"]),
            "tipo_documento": d["tipo_documento"], "numero_documento": numero}

    if tipo == "persona":
        requeridos(d, ["nombres", "apellidos", "fecha_nacimiento"])
        if d["tipo_documento"] not in DOC_PERSONA:
            raise ApiError(400, "Tipo de documento no válido para persona natural.", "documento_invalido")
        validar_documento(d["tipo_documento"], numero)
        if _edad(d["fecha_nacimiento"]) < 18:
            raise ApiError(422, "Debes ser mayor de edad para registrarte.", "menor_de_edad")
        nombres, apellidos = texto(d["nombres"], "nombres"), texto(d["apellidos"], "apellidos")
        base.update({
            "nombre": f"{nombres} {apellidos}", "nombres": nombres, "apellidos": apellidos,
            "fecha_nacimiento": d["fecha_nacimiento"],
            "ocupacion": d.get("ocupacion") if d.get("ocupacion") in OCUPACIONES else None,
            "pep": bool(d.get("pep", False)),
        })
    else:
        requeridos(d, ["razon_social", "representante"])
        if d["tipo_documento"] != "RUC":
            raise ApiError(400, "Las empresas se registran con RUC.", "documento_invalido")
        validar_documento("RUC", numero)
        rep = d["representante"]
        if not isinstance(rep, dict):
            raise ApiError(400, "Datos del representante inválidos.", "representante_invalido")
        requeridos(rep, ["nombre", "tipo_documento", "numero_documento", "cargo"])
        if rep["tipo_documento"] not in DOC_PERSONA:
            raise ApiError(400, "Documento del representante no válido.", "documento_invalido")
        validar_documento(rep["tipo_documento"], str(rep["numero_documento"]), "representante")
        razon = texto(d["razon_social"], "razon_social", 2, 150)
        base.update({
            "nombre": razon, "razon_social": razon,
            "actividad": d.get("actividad") if d.get("actividad") in ACTIVIDADES else None,
            "representante": {"nombre": texto(rep["nombre"], "representante.nombre"),
                              "tipo_documento": rep["tipo_documento"],
                              "numero_documento": str(rep["numero_documento"]),
                              "cargo": texto(rep["cargo"], "representante.cargo")},
        })
    base["_password"] = d["password"]
    return {k: v for k, v in base.items() if v is not None}


def registro(event):
    datos = _validar_registro(cuerpo_json(event))
    password = datos.pop("_password")
    id_cliente = nuevo_id("CLI-", 6)
    cliente = {"pk": f"CLI#{id_cliente}", "id_cliente": id_cliente, **datos,
               "password_hash": hash_password(password), "fecha_registro": iso(ahora())}
    nueva = "attribute_not_exists(pk)"
    try:
        tabla = _tabla()
        tabla.meta.client.transact_write_items(TransactItems=[
            {"Put": {"TableName": tabla.name, "Item": {"pk": f"EMAIL#{datos['correo']}", "id_cliente": id_cliente},
                     "ConditionExpression": nueva}},
            {"Put": {"TableName": tabla.name,
                     "Item": {"pk": f"DOC#{datos['tipo_documento']}#{datos['numero_documento']}", "id_cliente": id_cliente},
                     "ConditionExpression": nueva}},
            {"Put": {"TableName": tabla.name, "Item": cliente, "ConditionExpression": nueva}},
        ])
    except ClientError as e:
        if e.response["Error"]["Code"] == "TransactionCanceledException":
            razones = [r.get("Code") for r in e.response.get("CancellationReasons", [])]
            if razones and razones[0] == "ConditionalCheckFailed":
                raise ApiError(409, "Ya existe una cuenta con ese correo. Inicia sesión o usa otro correo.", "correo_duplicado")
            if len(razones) > 1 and razones[1] == "ConditionalCheckFailed":
                raise ApiError(409, "Ya existe una cuenta con ese número de documento.", "documento_duplicado")
            raise ApiError(409, "Ya existe una cuenta con esos datos.", "cliente_duplicado")
        raise
    log("cliente_registrado", id_cliente=id_cliente, tipo=datos["tipo_cliente"])
    return 201, {"id_cliente": id_cliente, "mensaje": "Cliente registrado"}


# --------------------------------------------------------------------- login
def login(event):
    d = cuerpo_json(event)
    requeridos(d, ["correo", "password"])
    correo = str(d["correo"]).strip().lower()
    tabla = _tabla()
    idx = tabla.get_item(Key={"pk": f"EMAIL#{correo}"}).get("Item")
    cliente = tabla.get_item(Key={"pk": f"CLI#{idx['id_cliente']}"}).get("Item") if idx else None
    # Mismo mensaje y mismo trabajo de hash para no revelar si el correo existe.
    almacenado = cliente["password_hash"] if cliente else hash_password("relleno-tiempo-constante")
    ok = verificar_password(str(d["password"]), almacenado)
    if not cliente or not ok:
        log("login_fallido")
        raise ApiError(401, "Correo o contraseña incorrectos.", "credenciales_invalidas")
    secreto = os.environ["JWT_SECRET"]
    ttl = int(os.environ.get("JWT_TTL_SEG", "7200"))
    token = jwt_crear({"sub": cliente["id_cliente"], "nombre": cliente["nombre"],
                       "tipo": cliente["tipo_cliente"]}, secreto, ttl)
    log("login_ok", id_cliente=cliente["id_cliente"])
    return 200, {"token": token, "expira_en": ttl, "cliente": _perfil_publico(cliente)}


# ------------------------------------------------------------------- perfil
def obtener_cliente(event):
    claims = exigir_sesion(event)
    id_cliente = parametro_ruta(event, "id_cliente")
    if claims["sub"] != id_cliente:  # nadie puede leer el perfil de otro cliente
        raise ApiError(403, "No tienes permiso para ver este perfil.", "prohibido")
    c = _tabla().get_item(Key={"pk": f"CLI#{id_cliente}"}).get("Item")
    if not c:
        raise ApiError(404, "No encontramos al cliente.", "no_encontrado")
    return 200, _perfil_publico(c)


handler = manejar({
    "POST /registro": registro,
    "POST /login": login,
    "GET /clientes/{id_cliente}": obtener_cliente,
})

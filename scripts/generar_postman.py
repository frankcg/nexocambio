#!/usr/bin/env python3
"""Genera postman/NexoCambio.postman_collection.json (Postman v2.1) con pruebas automáticas."""
import json
from pathlib import Path

PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
H = lambda k, v: {"key": k, "value": v}
JSON_H = H("Content-Type", "application/json")
AUTH = H("Authorization", "Bearer {{token}}")
ADMIN = H("x-admin-key", "{{adminKey}}")


def req(nombre, metodo, ruta, cuerpo=None, headers=(), test="", pre="", desc=""):
    partes = ruta.strip("/").split("/")
    r = {"method": metodo, "header": [JSON_H, *headers] if cuerpo is not None else list(headers),
         "url": {"raw": "{{baseUrl}}/" + "/".join(partes), "host": ["{{baseUrl}}"], "path": partes}, "description": desc}
    if cuerpo is not None:
        r["body"] = {"mode": "raw", "raw": json.dumps(cuerpo, indent=2, ensure_ascii=False),
                     "options": {"raw": {"language": "json"}}}
    ev = []
    if pre:
        ev.append({"listen": "prerequest", "script": {"type": "text/javascript", "exec": pre.strip().splitlines()}})
    if test:
        ev.append({"listen": "test", "script": {"type": "text/javascript", "exec": test.strip().splitlines()}})
    return {"name": nombre, "event": ev, "request": r}


def t_status(code, extra=""):
    return f'pm.test("Status {code}", () => pm.response.to.have.status({code}));\n{extra}'


def t_error(code, codigo):
    return t_status(code, f'pm.test("Código de error {codigo}", () => pm.expect(pm.response.json().codigo).to.eql("{codigo}"));')


COT = {"modalidad": "casa", "moneda_origen": "PEN", "moneda_destino": "USD", "monto_origen": 1000}
PRE_REG = """
const n = Date.now();
pm.collectionVariables.set("correo", "cliente" + n + "@nexocambio.pe");
pm.collectionVariables.set("dni", String(10000000 + Math.floor(Math.random() * 89999999)));
"""
REG = {"tipo_cliente": "persona", "nombres": "Lucía", "apellidos": "Ramírez Torres", "tipo_documento": "DNI",
       "numero_documento": "{{dni}}", "fecha_nacimiento": "1994-05-10", "telefono": "987654321",
       "ocupacion": "Dependiente", "pep": False, "correo": "{{correo}}", "password": "{{password}}"}
DEST = {"tipo": "banco", "banco": "Interbank", "tipo_cuenta": "Ahorros", "numero": "8983141592653", "titular": "Lucía Ramírez Torres"}

carpetas = [
    ("1. Cotizaciones (público)", [
        req("Cotizar - Casa de Cambio (PEN→USD)", "POST", "cotizar", COT,
            test=t_status(201, 'const j = pm.response.json();\npm.test("Devuelve tasa y monto", () => { pm.expect(j.tasa).to.be.above(0); pm.expect(j.monto_destino).to.be.above(0); });\npm.collectionVariables.set("id_cotizacion_demo", j.id_cotizacion);'),
            desc="Calcula tasa y monto estimado. Vigencia 5 minutos."),
        req("Cotizar - Cripto (PEN→USDT)", "POST", "cotizar", {**COT, "modalidad": "cripto", "moneda_destino": "USDT"}, test=t_status(201)),
        req("Cotizar - error: monedas iguales", "POST", "cotizar", {**COT, "moneda_destino": "PEN"}, test=t_status(422)),
        req("Cotizar - error: monto menor a US$ 10", "POST", "cotizar", {**COT, "monto_origen": 5}, test=t_status(422)),
    ]),
    ("2. Clientes y autenticación", [
        req("Registro - persona natural", "POST", "registro", REG, pre=PRE_REG,
            test=t_status(201, 'pm.collectionVariables.set("id_cliente", pm.response.json().id_cliente);')),
        req("Registro - error: correo duplicado", "POST", "registro", REG, test=t_status(409)),
        req("Login", "POST", "login", {"correo": "{{correo}}", "password": "{{password}}"},
            test=t_status(200, 'const j = pm.response.json();\npm.test("Devuelve JWT", () => pm.expect(j.token.split(".")).to.have.length(3));\npm.test("No expone el hash", () => pm.expect(JSON.stringify(j)).to.not.include("password_hash"));\npm.collectionVariables.set("token", j.token);\npm.collectionVariables.set("id_cliente", j.cliente.id_cliente);')),
        req("Login - error: contraseña incorrecta", "POST", "login", {"correo": "{{correo}}", "password": "Incorrecta99"}, test=t_status(401)),
        req("Consultar perfil", "GET", "clientes/{{id_cliente}}", headers=[AUTH], test=t_status(200)),
        req("Consultar perfil - error: sin token", "GET", "clientes/{{id_cliente}}", test=t_status(401)),
    ]),
    ("3. Operaciones (requiere login)", [
        req("Paso 1 - Cotizar", "POST", "cotizar", COT,
            test=t_status(201, 'pm.collectionVariables.set("id_cotizacion", pm.response.json().id_cotizacion);')),
        req("Paso 2 - Registrar operación", "POST", "operaciones",
            {"id_cotizacion": "{{id_cotizacion}}", "origen": {"tipo": "banco", "banco": "BCP"}, "destino": DEST}, headers=[AUTH],
            test=t_status(201, 'const j = pm.response.json();\npm.test("Estado inicial", () => pm.expect(j.estado).to.eql("Pendiente de comprobante"));\npm.collectionVariables.set("id_operacion", j.id_operacion);'),
            desc="El servidor toma tasa y montos de la cotización; ignora los que envíe el cliente."),
        req("Paso 3 - Adjuntar comprobante", "POST", "operaciones/{{id_operacion}}/comprobante",
            {"nombre_archivo": "transferencia.png", "content_type": "image/png", "contenido_base64": PNG, "numero_transferencia": "778899"}, headers=[AUTH],
            test=t_status(200, 'pm.test("Queda pendiente de validación", () => pm.expect(pm.response.json().estado).to.eql("Pendiente de validación"));')),
        req("Paso 4 - Mis operaciones", "GET", "operaciones", headers=[AUTH],
            test=t_status(200, 'pm.test("Lista con al menos 1", () => pm.expect(pm.response.json().total).to.be.above(0));')),
        req("Paso 5 - Detalle de operación", "GET", "operaciones/{{id_operacion}}", headers=[AUTH],
            test=t_status(200, 'pm.test("Incluye URL temporal del comprobante", () => pm.expect(pm.response.json().comprobante_url).to.include("https://"));')),
        req("Registrar operación - error: cotización ya usada", "POST", "operaciones",
            {"id_cotizacion": "{{id_cotizacion}}", "origen": {"tipo": "banco", "banco": "BCP"}, "destino": DEST}, headers=[AUTH], test=t_status(409)),
        req("Mis operaciones - error: sin token", "GET", "operaciones", test=t_status(401)),
    ]),
    ("4. Back-office simulado (x-admin-key)", [
        req("Listar todas las operaciones (back-office)", "GET", "operaciones/admin", headers=[ADMIN],
            test=t_status(200, 'const j = pm.response.json();\npm.test("Incluye la operación del paso 2", () => pm.expect(j.operaciones.map(o => o.id_operacion)).to.include(pm.collectionVariables.get("id_operacion")));\npm.test("Excluye los borradores", () => pm.expect(j.operaciones.every(o => o.estado !== "Pendiente de comprobante")).to.be.true);\npm.test("total coincide con la lista", () => pm.expect(j.total).to.eql(j.operaciones.length));'),
            desc="Cola de revisión: operaciones de TODOS los clientes, más recientes primero (máx. 200). No incluye las que aún no tienen comprobante."),
        req("Detalle de operación (back-office)", "GET", "operaciones/{{id_operacion}}/admin", headers=[ADMIN],
            test=t_status(200, 'const j = pm.response.json();\npm.test("Pendiente de validación", () => pm.expect(j.estado).to.eql("Pendiente de validación"));\npm.test("Incluye URL temporal del comprobante", () => pm.expect(j.comprobante_url).to.include("https://"));\npm.test("Incluye historial", () => pm.expect(j.historial).to.be.an("array").that.is.not.empty);'),
            desc="Detalle de cualquier operación, sin restricción de dueño."),
        req("Estado → En proceso", "PATCH", "operaciones/{{id_operacion}}/estado", {"estado": "En proceso"}, headers=[ADMIN],
            test=t_status(200, 'const j = pm.response.json();\npm.test("Estado En proceso", () => pm.expect(j.estado).to.eql("En proceso"));\npm.test("Conserva el comprobante", () => pm.expect(j.comprobante_url).to.include("https://"));')),
        req("Estado → Procesada", "PATCH", "operaciones/{{id_operacion}}/estado", {"estado": "Procesada"}, headers=[ADMIN],
            test=t_status(200, 'pm.test("Estado Procesada", () => pm.expect(pm.response.json().estado).to.eql("Procesada"));')),
        req("Estado - error: transición inválida (Procesada → En proceso)", "PATCH", "operaciones/{{id_operacion}}/estado", {"estado": "En proceso"}, headers=[ADMIN],
            test=t_error(409, "transicion_invalida")),
        req("Estado - error: sin clave de back-office", "PATCH", "operaciones/{{id_operacion}}/estado", {"estado": "Rechazada", "motivo_rechazo": "prueba"}, test=t_error(403, "prohibido")),
        req("Listar (back-office) - error: sin clave", "GET", "operaciones/admin", test=t_error(403, "prohibido")),
        req("Listar (back-office) - error: el JWT de un cliente no basta", "GET", "operaciones/admin", headers=[AUTH], test=t_error(403, "prohibido"),
            desc="Un cliente autenticado no puede entrar al back-office: solo cuenta la cabecera x-admin-key."),
        req("Detalle (back-office) - error: operación inexistente", "GET", "operaciones/OP-NO-EXISTE/admin", headers=[ADMIN], test=t_error(404, "no_encontrada")),
    ]),
    ("5. Rechazo desde el back-office", [
        req("Preparar - Cotizar", "POST", "cotizar", COT,
            test=t_status(201, 'pm.collectionVariables.set("id_cotizacion_rechazo", pm.response.json().id_cotizacion);')),
        req("Preparar - Registrar operación", "POST", "operaciones",
            {"id_cotizacion": "{{id_cotizacion_rechazo}}", "origen": {"tipo": "banco", "banco": "BCP"}, "destino": DEST}, headers=[AUTH],
            test=t_status(201, 'pm.collectionVariables.set("id_operacion_rechazo", pm.response.json().id_operacion);')),
        req("Preparar - Adjuntar comprobante", "POST", "operaciones/{{id_operacion_rechazo}}/comprobante",
            {"nombre_archivo": "transferencia.png", "content_type": "image/png", "contenido_base64": PNG, "numero_transferencia": "112233"}, headers=[AUTH],
            test=t_status(200, 'pm.test("Queda pendiente de validación", () => pm.expect(pm.response.json().estado).to.eql("Pendiente de validación"));')),
        req("Rechazar - error: sin motivo", "PATCH", "operaciones/{{id_operacion_rechazo}}/estado", {"estado": "Rechazada"}, headers=[ADMIN],
            test=t_error(400, "longitud_invalida"), desc="El motivo es obligatorio (3 a 300 caracteres) al rechazar."),
        req("Rechazar con motivo", "PATCH", "operaciones/{{id_operacion_rechazo}}/estado",
            {"estado": "Rechazada", "motivo_rechazo": "El comprobante no coincide con el monto"}, headers=[ADMIN],
            test=t_status(200, 'const j = pm.response.json();\npm.test("Estado Rechazada", () => pm.expect(j.estado).to.eql("Rechazada"));\npm.test("Guarda el motivo", () => pm.expect(j.motivo_rechazo).to.eql("El comprobante no coincide con el monto"));\npm.test("Conserva el comprobante", () => pm.expect(j.comprobante_url).to.include("https://"));')),
        req("El cliente ve el rechazo y su motivo", "GET", "operaciones/{{id_operacion_rechazo}}", headers=[AUTH],
            test=t_status(200, 'const j = pm.response.json();\npm.test("Estado Rechazada", () => pm.expect(j.estado).to.eql("Rechazada"));\npm.test("Muestra el motivo", () => pm.expect(j.motivo_rechazo).to.include("no coincide"));')),
        req("Estado - error: una Rechazada no se reabre", "PATCH", "operaciones/{{id_operacion_rechazo}}/estado", {"estado": "En proceso"}, headers=[ADMIN],
            test=t_error(409, "transicion_invalida")),
    ]),
]
col = {
    "info": {"name": "NexoCambio API", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
             "description": "Ejecutar en orden (Runner). Configure baseUrl con la salida ApiUrl del despliegue, o http://localhost:8787 con el servidor local, y adminKey con la clave de back-office (la imprime deploy.sh; en local es admin-local)."},
    "item": [{"name": n, "item": items} for n, items in carpetas],
    "variable": [{"key": "baseUrl", "value": "http://localhost:8787"}, {"key": "password", "value": "Clave1234"},
                 {"key": "adminKey", "value": "admin-local"}, {"key": "token", "value": ""}, {"key": "id_cliente", "value": ""},
                 {"key": "id_cotizacion", "value": ""}, {"key": "id_operacion", "value": ""},
                 {"key": "id_cotizacion_rechazo", "value": ""}, {"key": "id_operacion_rechazo", "value": ""},
                 {"key": "correo", "value": ""}, {"key": "dni", "value": ""}],
}
ruta = Path(__file__).resolve().parents[1] / "postman" / "NexoCambio.postman_collection.json"
ruta.write_text(json.dumps(col, indent=2, ensure_ascii=False), encoding="utf-8")
print("Generado", ruta, "-", sum(len(i) for _, i in carpetas), "requests")

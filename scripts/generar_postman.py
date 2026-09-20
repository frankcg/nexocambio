#!/usr/bin/env python3
"""Genera postman/NexoCambio.postman_collection.json (Postman v2.1) con pruebas automáticas."""
import json
from pathlib import Path

PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
H = lambda k, v: {"key": k, "value": v}
JSON_H = H("Content-Type", "application/json")
AUTH = H("Authorization", "Bearer {{token}}")


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
        req("Estado → En proceso", "PATCH", "operaciones/{{id_operacion}}/estado", {"estado": "En proceso"}, headers=[H("x-admin-key", "{{adminKey}}")], test=t_status(200)),
        req("Estado → Procesada", "PATCH", "operaciones/{{id_operacion}}/estado", {"estado": "Procesada"}, headers=[H("x-admin-key", "{{adminKey}}")], test=t_status(200)),
        req("Estado - error: sin clave de back-office", "PATCH", "operaciones/{{id_operacion}}/estado", {"estado": "Rechazada", "motivo_rechazo": "prueba"}, test=t_status(403)),
    ]),
]
col = {
    "info": {"name": "NexoCambio API", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
             "description": "Ejecutar en orden (Runner). Configure baseUrl con la salida ApiUrl del despliegue, o http://localhost:8787 con el servidor local."},
    "item": [{"name": n, "item": items} for n, items in carpetas],
    "variable": [{"key": "baseUrl", "value": "http://localhost:8787"}, {"key": "password", "value": "Clave1234"},
                 {"key": "adminKey", "value": "admin-local"}, {"key": "token", "value": ""}, {"key": "id_cliente", "value": ""},
                 {"key": "id_cotizacion", "value": ""}, {"key": "id_operacion", "value": ""}, {"key": "correo", "value": ""}, {"key": "dni", "value": ""}],
}
ruta = Path(__file__).resolve().parents[1] / "postman" / "NexoCambio.postman_collection.json"
ruta.write_text(json.dumps(col, indent=2, ensure_ascii=False), encoding="utf-8")
print("Generado", ruta, "-", sum(len(i) for _, i in carpetas), "requests")

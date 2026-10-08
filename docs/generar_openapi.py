#!/usr/bin/env python3
"""Genera docs/openapi.json (OpenAPI 3.0.3) y docs/openapi.html (Swagger UI, spec embebido).

Documenta el contrato real de la API (ver CLAUDE.md y los `app.py` de cada
microservicio). Es solo documentación: no se usa como DefinitionBody del API
Gateway en template.yaml, que sigue definido con eventos SAM.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

BANCOS = ["BCP", "Interbank", "BBVA", "Scotiabank", "BanBif", "Banco Pichincha"]
MONEDAS = ["PEN", "USD", "EUR", "USDT", "USDC", "BTC", "ETH"]
ESTADOS = ["Pendiente de validación", "En proceso", "Procesada", "Rechazada"]


def err(status: int, descripcion: str, *codigos: str) -> dict:
    """Respuesta de error {mensaje, codigo}; `codigos` son los valores reales que puede traer `codigo`."""
    return {
        "description": f"{descripcion} Valores posibles de `codigo`: " + ", ".join(f"`{c}`" for c in codigos) + ".",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"},
                                          "example": {"mensaje": descripcion, "codigo": codigos[0]}}},
    }


def ok(status_desc: str, esquema: str, ejemplo: dict | None = None) -> dict:
    c = {"schema": {"$ref": f"#/components/schemas/{esquema}"}}
    if ejemplo is not None:
        c["example"] = ejemplo
    return {"description": status_desc, "content": {"application/json": c}}


def cuerpo(esquema: str, ejemplo: dict | None = None) -> dict:
    c = {"schema": {"$ref": f"#/components/schemas/{esquema}"}}
    if ejemplo is not None:
        c["example"] = ejemplo
    return {"required": True, "content": {"application/json": c}}


AUTH = [{"bearerAuth": []}]
ADMIN = [{"adminKey": []}]

COT_EJ = {"id_cotizacion": "COT-A1B2C3D4", "modalidad": "casa", "moneda_origen": "PEN", "moneda_destino": "USD",
          "monto_origen": 1000, "tasa": 3.7421, "tasa_preferencial": False, "monto_destino": 267.23,
          "fuente_tasas": "en_vivo", "fecha_cotizacion": "2026-10-06T15:04:00.000Z",
          "fecha_expiracion": "2026-10-06T15:09:00.000Z"}

OPERACION_EJ = {"id_operacion": "NX-A1B2C3D4", "id_cliente": "CLI-X1Y2Z3", "id_cotizacion": "COT-A1B2C3D4",
                "modalidad": "casa", "moneda_origen": "PEN", "moneda_destino": "USD", "monto_origen": 1000,
                "monto_destino": 267.23, "tasa": 3.7421, "tasa_preferencial": False,
                "estado": "Pendiente de validación", "fecha_operacion": "2026-10-06T15:05:00.000Z",
                "historial": [{"estado": "Pendiente de validación", "fecha": "2026-10-06T15:06:00.000Z"}],
                "origen": {"tipo": "banco", "banco": "BCP"},
                "destino": {"tipo": "banco", "banco": "Interbank", "tipo_cuenta": "Ahorros",
                            "numero": "8983141592653", "titular": "Lucía Ramírez Torres"},
                "comprobante_nombre": "transferencia.png", "comprobante_tipo": "image/png",
                "comprobante_tamano": 54821, "numero_transferencia": "778899",
                "comprobante_url": "https://.../comprobantes/CLI-X1Y2Z3/NX-A1B2C3D4/transferencia.png?..."}

ESQUEMAS = {
    "Error": {
        "type": "object", "required": ["mensaje", "codigo"],
        "properties": {"mensaje": {"type": "string", "description": "Mensaje para mostrar al usuario, en español."},
                        "codigo": {"type": "string", "description": "Código estable para manejar el error en el front."}},
    },
    "Cotizacion": {
        "type": "object",
        "properties": {
            "id_cotizacion": {"type": "string", "example": "COT-A1B2C3D4"},
            "modalidad": {"type": "string", "enum": ["casa", "cripto"]},
            "moneda_origen": {"type": "string", "enum": MONEDAS},
            "moneda_destino": {"type": "string", "enum": MONEDAS},
            "monto_origen": {"type": "number"},
            "tasa": {"type": "number", "description": "moneda_destino por 1 moneda_origen, ya con el spread aplicado."},
            "tasa_preferencial": {"type": "boolean", "description": "true si el monto en USD alcanzó el umbral preferencial (spread reducido 40 %)."},
            "monto_destino": {"type": "number"},
            "fuente_tasas": {"type": "string", "enum": ["en_vivo", "cache", "referencial"]},
            "fecha_cotizacion": {"type": "string", "format": "date-time"},
            "fecha_expiracion": {"type": "string", "format": "date-time", "description": "Vigencia: 5 minutos desde la emisión (configurable)."},
        },
    },
    "CotizarRequest": {
        "type": "object", "required": ["modalidad", "moneda_origen", "moneda_destino", "monto_origen"],
        "properties": {
            "modalidad": {"type": "string", "enum": ["casa", "cripto"]},
            "moneda_origen": {"type": "string", "enum": MONEDAS},
            "moneda_destino": {"type": "string", "enum": MONEDAS},
            "monto_origen": {"type": "number", "minimum": 0, "exclusiveMinimum": True,
                              "description": "Equivalente entre US$ 10 y US$ 1,000,000."},
        },
        "description": "Modalidad 'casa': PEN/USD/EUR entre sí. Modalidad 'cripto': PEN o USD contra USDT/USDC/BTC/ETH (un extremo debe ser cripto).",
    },
    "ExtremoBanco": {
        "type": "object", "required": ["tipo", "banco"],
        "properties": {
            "tipo": {"type": "string", "enum": ["banco"]},
            "banco": {"type": "string", "enum": BANCOS},
            "tipo_cuenta": {"type": "string", "enum": ["Ahorros", "Corriente"], "description": "Solo en el destino."},
            "numero": {"type": "string", "pattern": r"^\d{10,20}$", "description": "Número de cuenta o CCI. Solo en el destino."},
            "titular": {"type": "string", "minLength": 2, "maxLength": 150, "description": "Solo en el destino."},
        },
        "description": "Para monedas fiat (PEN, USD, EUR).",
    },
    "ExtremoWallet": {
        "type": "object", "required": ["tipo", "red"],
        "properties": {
            "tipo": {"type": "string", "enum": ["wallet"]},
            "red": {"type": "string", "description": "USDT: TRON (TRC20) o Ethereum (ERC20) · USDC: Ethereum (ERC20) o Solana · BTC: Bitcoin · ETH: Ethereum (ERC20)."},
            "direccion": {"type": "string", "pattern": "^[A-Za-z0-9]{26,64}$", "description": "Solo en el destino."},
        },
        "description": "Para criptoactivos (USDT, USDC, BTC, ETH).",
    },
    "Extremo": {
        "oneOf": [{"$ref": "#/components/schemas/ExtremoBanco"}, {"$ref": "#/components/schemas/ExtremoWallet"}],
        "discriminator": {"propertyName": "tipo", "mapping": {"banco": "#/components/schemas/ExtremoBanco", "wallet": "#/components/schemas/ExtremoWallet"}},
    },
    "Representante": {
        "type": "object", "required": ["nombre", "tipo_documento", "numero_documento", "cargo"],
        "properties": {
            "nombre": {"type": "string"},
            "tipo_documento": {"type": "string", "enum": ["DNI", "CE", "Pasaporte"]},
            "numero_documento": {"type": "string"},
            "cargo": {"type": "string"},
        },
    },
    "RegistroPersona": {
        "type": "object",
        "required": ["tipo_cliente", "tipo_documento", "numero_documento", "telefono", "correo", "password", "nombres", "apellidos", "fecha_nacimiento"],
        "properties": {
            "tipo_cliente": {"type": "string", "enum": ["persona"]},
            "tipo_documento": {"type": "string", "enum": ["DNI", "CE", "Pasaporte"]},
            "numero_documento": {"type": "string", "description": "DNI: 8 dígitos · CE: 9-12 alfanum. · Pasaporte: 6-12 alfanum."},
            "telefono": {"type": "string", "pattern": r"^9\d{8}$", "description": "9 dígitos, empieza con 9."},
            "correo": {"type": "string", "format": "email"},
            "password": {"type": "string", "minLength": 8, "description": "Mínimo 8 caracteres, con letras y números."},
            "nombres": {"type": "string"},
            "apellidos": {"type": "string"},
            "fecha_nacimiento": {"type": "string", "format": "date", "description": "Debe ser mayor de edad."},
            "ocupacion": {"type": "string", "enum": ["Dependiente", "Independiente", "Empresario", "Estudiante", "Jubilado", "Otro"]},
            "pep": {"type": "boolean", "default": False, "description": "Persona Expuesta Políticamente."},
        },
    },
    "RegistroEmpresa": {
        "type": "object",
        "required": ["tipo_cliente", "tipo_documento", "numero_documento", "telefono", "correo", "password", "razon_social", "representante"],
        "properties": {
            "tipo_cliente": {"type": "string", "enum": ["empresa"]},
            "tipo_documento": {"type": "string", "enum": ["RUC"]},
            "numero_documento": {"type": "string", "pattern": r"^(10|15|17|20)\d{9}$", "description": "RUC: 11 dígitos."},
            "telefono": {"type": "string", "pattern": r"^9\d{8}$"},
            "correo": {"type": "string", "format": "email"},
            "password": {"type": "string", "minLength": 8},
            "razon_social": {"type": "string", "minLength": 2, "maxLength": 150},
            "actividad": {"type": "string", "enum": ["Comercio", "Servicios", "Manufactura", "Tecnología", "Construcción", "Otro"]},
            "representante": {"$ref": "#/components/schemas/Representante"},
        },
    },
    "RegistroRequest": {
        "oneOf": [{"$ref": "#/components/schemas/RegistroPersona"}, {"$ref": "#/components/schemas/RegistroEmpresa"}],
        "discriminator": {"propertyName": "tipo_cliente", "mapping": {"persona": "#/components/schemas/RegistroPersona", "empresa": "#/components/schemas/RegistroEmpresa"}},
    },
    "RegistroResponse": {
        "type": "object", "properties": {"id_cliente": {"type": "string", "example": "CLI-X1Y2Z3"}, "mensaje": {"type": "string"}},
    },
    "LoginRequest": {
        "type": "object", "required": ["correo", "password"],
        "properties": {"correo": {"type": "string", "format": "email"}, "password": {"type": "string"}},
    },
    "Cliente": {
        "type": "object",
        "description": "Perfil público (sin password_hash). Persona natural o empresa, según tipo_cliente.",
        "properties": {
            "id_cliente": {"type": "string"},
            "tipo_cliente": {"type": "string", "enum": ["persona", "empresa"]},
            "nombre": {"type": "string", "description": "Nombre completo o razón social, para mostrar en pantalla."},
            "correo": {"type": "string", "format": "email"},
            "telefono": {"type": "string"},
            "tipo_documento": {"type": "string"},
            "numero_documento": {"type": "string"},
            "fecha_registro": {"type": "string", "format": "date-time"},
            "nombres": {"type": "string", "description": "Solo persona."},
            "apellidos": {"type": "string", "description": "Solo persona."},
            "fecha_nacimiento": {"type": "string", "format": "date", "description": "Solo persona."},
            "ocupacion": {"type": "string", "description": "Solo persona."},
            "pep": {"type": "boolean", "description": "Solo persona."},
            "razon_social": {"type": "string", "description": "Solo empresa."},
            "actividad": {"type": "string", "description": "Solo empresa."},
            "representante": {"allOf": [{"$ref": "#/components/schemas/Representante"}], "description": "Solo empresa."},
        },
    },
    "LoginResponse": {
        "type": "object",
        "properties": {
            "token": {"type": "string", "description": "JWT HS256, cabecera Authorization: Bearer <token>."},
            "expira_en": {"type": "integer", "description": "Segundos de vigencia del token (por defecto 7200).", "example": 7200},
            "cliente": {"$ref": "#/components/schemas/Cliente"},
        },
    },
    "CrearOperacionRequest": {
        "type": "object", "required": ["id_cotizacion", "origen", "destino"],
        "properties": {
            "id_cotizacion": {"type": "string", "description": "De una cotización vigente (POST /cotizar). Se usa una sola vez."},
            "origen": {"$ref": "#/components/schemas/Extremo"},
            "destino": {"$ref": "#/components/schemas/Extremo"},
        },
        "description": "El servidor toma moneda/monto/tasa de la cotización; ignora los que envíe el cliente (si los envía, deben coincidir).",
    },
    "HistorialItem": {
        "type": "object", "properties": {"estado": {"type": "string", "enum": ESTADOS}, "fecha": {"type": "string", "format": "date-time"}},
    },
    "Operacion": {
        "type": "object",
        "properties": {
            "id_operacion": {"type": "string", "example": "NX-A1B2C3D4"},
            "id_cliente": {"type": "string"},
            "id_cotizacion": {"type": "string"},
            "modalidad": {"type": "string", "enum": ["casa", "cripto"]},
            "moneda_origen": {"type": "string", "enum": MONEDAS},
            "moneda_destino": {"type": "string", "enum": MONEDAS},
            "monto_origen": {"type": "number"},
            "monto_destino": {"type": "number"},
            "tasa": {"type": "number"},
            "tasa_preferencial": {"type": "boolean"},
            "estado": {"type": "string", "enum": ESTADOS, "description": "'Pendiente de comprobante' es un estado interno previo (borrador); nunca se devuelve en las listas."},
            "fecha_operacion": {"type": "string", "format": "date-time"},
            "historial": {"type": "array", "items": {"$ref": "#/components/schemas/HistorialItem"}},
            "origen": {"$ref": "#/components/schemas/Extremo"},
            "destino": {"$ref": "#/components/schemas/Extremo"},
            "comprobante_nombre": {"type": "string", "description": "Presente desde que se adjunta el comprobante."},
            "comprobante_tipo": {"type": "string", "enum": ["image/jpeg", "image/png", "image/webp", "application/pdf"]},
            "comprobante_tamano": {"type": "integer", "description": "Bytes."},
            "numero_transferencia": {"type": "string"},
            "comprobante_url": {"type": "string", "format": "uri", "description": "URL firmada (S3), temporal (900 s). Solo en el detalle, no en los listados."},
            "motivo_rechazo": {"type": "string", "description": "Presente solo si estado es 'Rechazada'."},
        },
    },
    "OperacionesListResponse": {
        "type": "object",
        "properties": {"operaciones": {"type": "array", "items": {"$ref": "#/components/schemas/Operacion"}}, "total": {"type": "integer"}},
    },
    "ComprobanteRequest": {
        "type": "object", "required": ["nombre_archivo", "content_type", "contenido_base64"],
        "properties": {
            "nombre_archivo": {"type": "string"},
            "content_type": {"type": "string", "enum": ["image/jpeg", "image/png", "image/webp", "application/pdf"]},
            "contenido_base64": {"type": "string", "format": "byte", "description": "Archivo codificado en base64. Máx. 4 MB; el contenido real debe coincidir con content_type (se valida la firma del archivo)."},
            "numero_transferencia": {"type": "string", "maxLength": 40},
        },
    },
    "EstadoRequest": {
        "type": "object", "required": ["estado"],
        "properties": {
            "estado": {"type": "string", "enum": ["En proceso", "Procesada", "Rechazada"]},
            "motivo_rechazo": {"type": "string", "minLength": 3, "maxLength": 300, "description": "Obligatorio cuando estado es 'Rechazada'."},
        },
    },
}

PATHS = {
    "/cotizar": {"post": {
        "tags": ["Cotizaciones"], "summary": "Cotizar un cambio (casa o cripto)",
        "description": "Pública. Calcula tasa y monto estimado; la cotización queda vigente 5 minutos.",
        "requestBody": cuerpo("CotizarRequest", {"modalidad": "casa", "moneda_origen": "PEN", "moneda_destino": "USD", "monto_origen": 1000}),
        "responses": {
            "201": ok("Cotización creada.", "Cotizacion", COT_EJ),
            "400": err(400, "Cuerpo inválido o faltan campos.", "cuerpo_vacio", "cuerpo_invalido", "json_invalido", "campos_faltantes", "modalidad_invalida", "monto_invalido"),
            "422": err(422, "La combinación de datos no es válida.", "moneda_no_disponible", "monedas_iguales", "sin_cripto", "monto_invalido", "monto_minimo", "monto_maximo"),
        },
    }},
    "/registro": {"post": {
        "tags": ["Clientes y autenticación"], "summary": "Registrar un cliente (persona natural o empresa)",
        "description": "Pública.",
        "requestBody": cuerpo("RegistroRequest"),
        "responses": {
            "201": ok("Cliente registrado.", "RegistroResponse", {"id_cliente": "CLI-X1Y2Z3", "mensaje": "Cliente registrado"}),
            "400": err(400, "Cuerpo inválido o datos con formato incorrecto.", "cuerpo_vacio", "json_invalido", "campos_faltantes", "tipo_cliente_invalido",
                       "correo_invalido", "telefono_invalido", "password_debil", "documento_invalido", "fecha_invalida", "representante_invalido", "longitud_invalida"),
            "422": err(422, "Dato fuera de regla de negocio.", "menor_de_edad"),
            "409": err(409, "Ya existe una cuenta con ese correo o documento.", "correo_duplicado", "documento_duplicado", "cliente_duplicado"),
        },
    }},
    "/login": {"post": {
        "tags": ["Clientes y autenticación"], "summary": "Iniciar sesión",
        "description": "Pública. Devuelve un JWT HS256 vigente 2 horas (por defecto).",
        "requestBody": cuerpo("LoginRequest", {"correo": "demo@nexocambio.pe", "password": "Demo1234"}),
        "responses": {
            "200": ok("Sesión iniciada.", "LoginResponse"),
            "400": err(400, "Faltan campos.", "cuerpo_vacio", "campos_faltantes"),
            "401": err(401, "Correo o contraseña incorrectos.", "credenciales_invalidas"),
        },
    }},
    "/clientes/{id_cliente}": {"get": {
        "tags": ["Clientes y autenticación"], "summary": "Consultar el perfil propio",
        "description": "Requiere JWT. Solo el propio cliente puede ver su perfil.",
        "security": AUTH,
        "parameters": [{"name": "id_cliente", "in": "path", "required": True, "schema": {"type": "string"}}],
        "responses": {
            "200": ok("Perfil del cliente.", "Cliente"),
            "401": err(401, "Falta o es inválido el token.", "no_autenticado", "token_invalido", "sesion_expirada"),
            "403": err(403, "Intenta ver el perfil de otro cliente.", "prohibido"),
            "404": err(404, "El cliente no existe.", "no_encontrado"),
        },
    }},
    "/operaciones": {
        "post": {
            "tags": ["Operaciones"], "summary": "Registrar una operación a partir de una cotización vigente",
            "description": "Requiere JWT. Una cotización solo puede usarse una vez; el servidor no confía en tasa/montos enviados por el cliente.",
            "security": AUTH,
            "requestBody": cuerpo("CrearOperacionRequest"),
            "responses": {
                "201": ok("Operación registrada, en estado 'Pendiente de comprobante' (no se lista hasta adjuntar comprobante).", "Operacion"),
                "400": err(400, "Cuerpo inválido o faltan campos.", "cuerpo_vacio", "campos_faltantes"),
                "401": err(401, "Falta o es inválido el token.", "no_autenticado", "token_invalido", "sesion_expirada"),
                "404": err(404, "La cotización no existe o ya venció hace más de 10 minutos (gracia).", "cotizacion_no_encontrada"),
                "409": err(409, "La cotización venció o ya se usó.", "cotizacion_expirada", "cotizacion_usada"),
                "422": err(422, "Origen/destino inválidos para la moneda, o no coinciden con la cotización.",
                           "extremo_invalido", "banco_invalido", "cuenta_invalida", "tipo_cuenta_invalido", "red_invalida", "wallet_invalida", "cotizacion_inconsistente"),
                "502": err(502, "El microservicio de Cotizaciones no respondió.", "servicio_no_disponible"),
            },
        },
        "get": {
            "tags": ["Operaciones"], "summary": "Listar mis operaciones",
            "description": "Requiere JWT. Más recientes primero (máx. 200). No incluye borradores sin comprobante.",
            "security": AUTH,
            "responses": {
                "200": ok("Listado del cliente autenticado.", "OperacionesListResponse"),
                "401": err(401, "Falta o es inválido el token.", "no_autenticado", "token_invalido", "sesion_expirada"),
            },
        },
    },
    "/operaciones/{id_operacion}": {"get": {
        "tags": ["Operaciones"], "summary": "Detalle de una operación propia",
        "description": "Requiere JWT. Incluye historial y la URL temporal del comprobante (900 s).",
        "security": AUTH,
        "parameters": [{"name": "id_operacion", "in": "path", "required": True, "schema": {"type": "string"}}],
        "responses": {
            "200": ok("Detalle de la operación.", "Operacion", OPERACION_EJ),
            "401": err(401, "Falta o es inválido el token.", "no_autenticado", "token_invalido", "sesion_expirada"),
            "404": err(404, "No existe o no te pertenece (se devuelve 404, no 403, para no revelar su existencia).", "no_encontrada"),
        },
    }},
    "/operaciones/{id_operacion}/comprobante": {"post": {
        "tags": ["Operaciones"], "summary": "Adjuntar el comprobante de transferencia",
        "description": "Requiere JWT. JPG/PNG/WEBP/PDF, máx. 4 MB; el contenido real debe coincidir con el content_type declarado. Pasa el estado a 'Pendiente de validación'.",
        "security": AUTH,
        "parameters": [{"name": "id_operacion", "in": "path", "required": True, "schema": {"type": "string"}}],
        "requestBody": cuerpo("ComprobanteRequest"),
        "responses": {
            "200": ok("Comprobante registrado.", "Operacion"),
            "400": err(400, "Cuerpo inválido, faltan campos o el base64 no decodifica.", "cuerpo_vacio", "campos_faltantes", "archivo_invalido"),
            "401": err(401, "Falta o es inválido el token.", "no_autenticado", "token_invalido", "sesion_expirada"),
            "404": err(404, "No existe o no te pertenece.", "no_encontrada"),
            "409": err(409, "La operación ya no admite comprobante, o cambió de estado en paralelo.", "estado_invalido", "conflicto"),
            "413": err(413, "El archivo supera 4 MB.", "archivo_grande"),
            "422": err(422, "Formato no permitido o el contenido no coincide con el content_type.", "formato_no_permitido", "archivo_invalido"),
        },
    }},
    "/operaciones/admin": {"get": {
        "tags": ["Back-office (admin)"], "summary": "Listar TODAS las operaciones (cola de revisión)",
        "description": "Back-office simulado. Protegida con la cabecera x-admin-key (no JWT); sin ADMIN_KEY configurada, la ruta queda deshabilitada. Scan + orden por fecha, más recientes primero (máx. 200). Excluye borradores.",
        "security": ADMIN,
        "responses": {
            "200": ok("Listado de todos los clientes.", "OperacionesListResponse"),
            "403": err(403, "Falta la cabecera x-admin-key, es incorrecta, o se envió un JWT de cliente en su lugar.", "prohibido"),
        },
    }},
    "/operaciones/{id_operacion}/admin": {"get": {
        "tags": ["Back-office (admin)"], "summary": "Detalle de cualquier operación",
        "description": "Back-office simulado. Protegida con x-admin-key. Sin restricción de dueño.",
        "security": ADMIN,
        "parameters": [{"name": "id_operacion", "in": "path", "required": True, "schema": {"type": "string"}}],
        "responses": {
            "200": ok("Detalle de la operación, con la URL temporal del comprobante.", "Operacion"),
            "403": err(403, "Falta o es incorrecta la cabecera x-admin-key.", "prohibido"),
            "404": err(404, "La operación no existe.", "no_encontrada"),
        },
    }},
    "/operaciones/{id_operacion}/estado": {"patch": {
        "tags": ["Back-office (admin)"], "summary": "Avanzar el estado de una operación",
        "description": "Back-office simulado. Protegida con x-admin-key. Transiciones permitidas: "
                        "'Pendiente de validación' → {'En proceso', 'Rechazada'}; 'En proceso' → {'Procesada', 'Rechazada'}. "
                        "motivo_rechazo es obligatorio al rechazar.",
        "security": ADMIN,
        "parameters": [{"name": "id_operacion", "in": "path", "required": True, "schema": {"type": "string"}}],
        "requestBody": cuerpo("EstadoRequest", {"estado": "Rechazada", "motivo_rechazo": "El comprobante no coincide con el monto"}),
        "responses": {
            "200": ok("Estado actualizado, con historial y URL del comprobante.", "Operacion"),
            "400": err(400, "Falta el campo estado, o falta/longitud inválida de motivo_rechazo al rechazar.", "campos_faltantes", "longitud_invalida"),
            "403": err(403, "Falta o es incorrecta la cabecera x-admin-key.", "prohibido"),
            "404": err(404, "La operación no existe.", "no_encontrada"),
            "409": err(409, "La transición no está permitida desde el estado actual, o cambió en paralelo.", "transicion_invalida", "conflicto"),
        },
    }},
}

OPENAPI = {
    "openapi": "3.0.3",
    "info": {
        "title": "NexoCambio API",
        "version": "1.0.0",
        "description": (
            "Casa de cambio de divisas y cripto — API serverless (API Gateway HTTP API + 3 Lambdas + DynamoDB + S3).\n\n"
            "Formato JSON. Los errores siempre devuelven `{mensaje, codigo}`. Las rutas de cliente van con "
            "`Authorization: Bearer <token>` (JWT HS256, ver POST /login); las de back-office simulado van con la "
            "cabecera `x-admin-key` en vez de JWT. Si una ruta protegida responde 401, el front limpia la sesión y "
            "redirige a login.\n\n"
            "Este documento es solo de referencia (generado por docs/generar_openapi.py a partir del contrato real); "
            "el API Gateway sigue definido con eventos SAM en template.yaml, no con este spec."
        ),
    },
    "servers": [
        {"url": "https://{apiId}.execute-api.{region}.amazonaws.com/v1",
         "variables": {"apiId": {"default": "TU-API-ID"}, "region": {"default": "us-east-1"}},
         "description": "Despliegue en AWS (ver salida ApiUrl de deploy.sh)."},
        {"url": "http://localhost:8787", "description": "Servidor local (scripts/servidor_local.py)."},
    ],
    "tags": [
        {"name": "Cotizaciones"}, {"name": "Clientes y autenticación"},
        {"name": "Operaciones"}, {"name": "Back-office (admin)"},
    ],
    "components": {
        "securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
            "adminKey": {"type": "apiKey", "in": "header", "name": "x-admin-key"},
        },
        "schemas": ESQUEMAS,
    },
    "paths": PATHS,
}

HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>NexoCambio · Catálogo de API (OpenAPI)</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
<style>body {{ margin: 0; }}</style>
</head>
<body>
<div id="swagger-ui"></div>
<script id="spec" type="application/json">{spec_json}</script>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
  window.onload = function () {{
    SwaggerUIBundle({{
      spec: JSON.parse(document.getElementById('spec').textContent),
      dom_id: '#swagger-ui',
      presets: [SwaggerUIBundle.presets.apis],
      deepLinking: true,
    }});
  }};
</script>
</body>
</html>
"""

if __name__ == "__main__":
    spec_json = json.dumps(OPENAPI, indent=2, ensure_ascii=False)
    (RAIZ / "docs" / "openapi.json").write_text(spec_json, encoding="utf-8")
    (RAIZ / "docs" / "openapi.html").write_text(HTML.format(spec_json=spec_json), encoding="utf-8")
    print("Generado docs/openapi.json y docs/openapi.html -", len(PATHS), "rutas,", len(ESQUEMAS), "esquemas")

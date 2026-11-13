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
ESTADOS_VALIDACION = ["en_curso", "en_revision", "finalizada"]


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
BANCO = [{"bancoKey": []}]
SIN_TOKEN = err(401, "Falta o es inválido el token.", "no_autenticado", "token_invalido", "sesion_expirada")
SIN_ADMIN = err(403, "Falta o es incorrecta la cabecera x-admin-key.", "prohibido")
SIN_BANCO = err(403, "Falta o es incorrecta la cabecera x-banco-key (la clave del back-office no sirve).", "prohibido")
ID_OP = [{"name": "id_operacion", "in": "path", "required": True, "schema": {"type": "string"}}]

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
    # ------------------------------------------------------------------ NexoGuard (proyecto final)
    "ValidacionCliente": {
        "type": "object", "description": "Vista del cliente: solo el estado y el resultado, sin el análisis de la IA.",
        "properties": {
            "id_operacion": {"type": "string"},
            "estado": {"type": "string", "enum": ESTADOS_VALIDACION},
            "fecha_inicio": {"type": "string", "format": "date-time"},
            "fecha_fin": {"type": "string", "format": "date-time", "nullable": True},
            "estado_final": {"type": "string", "enum": ["En proceso", "Rechazada"], "nullable": True},
            "decidido_por": {"type": "string", "enum": ["agente", "operador"], "nullable": True},
            "motivo": {"type": "string", "nullable": True, "description": "Solo cuando la operación se rechazó."},
        },
    },
    "Extraccion": {
        "type": "object", "description": "Salida del Agente Extractor (Groq, visión).",
        "properties": {
            "es_comprobante": {"type": "boolean", "nullable": True}, "legible": {"type": "boolean"},
            "banco_origen": {"type": "string", "nullable": True}, "monto": {"type": "number", "nullable": True},
            "moneda": {"type": "string", "nullable": True}, "fecha": {"type": "string", "format": "date", "nullable": True},
            "hora": {"type": "string", "nullable": True}, "numero_operacion": {"type": "string", "nullable": True},
            "destinatario": {"type": "string", "nullable": True}, "cuenta_destino": {"type": "string", "nullable": True},
            "banco_destino": {"type": "string", "nullable": True},
            "confianza": {"type": "number", "minimum": 0, "maximum": 1}, "observaciones": {"type": "string"},
            "modelo": {"type": "string", "nullable": True},
        },
    },
    "ReglaVerificacion": {
        "type": "object", "description": "Resultado de una regla determinista (guard-verificar o la conciliación).",
        "properties": {
            "regla": {"type": "string", "example": "monto"},
            "resultado": {"type": "string", "enum": ["cumple", "no_cumple", "no_concluyente"]},
            "gravedad": {"type": "string", "enum": ["rechazo", "revision", "informativa"],
                         "description": "Qué pasa si no cumple: rechazo automático, revisión humana o nada."},
            "detalle": {"type": "string"},
        },
    },
    "Validacion": {
        "type": "object", "description": "Registro auditable completo (back-office). El task token de Step Functions nunca se expone.",
        "properties": {
            "id_operacion": {"type": "string"}, "fecha_inicio": {"type": "string", "format": "date-time"},
            "id_cliente": {"type": "string"}, "estado": {"type": "string", "enum": ESTADOS_VALIDACION},
            "monto_origen": {"type": "number"}, "moneda_origen": {"type": "string"}, "comprobante": {"type": "string"},
            "ejecucion_arn": {"type": "string", "description": "Ejecución de Step Functions."},
            "extraccion": {"$ref": "#/components/schemas/Extraccion"},
            "verificaciones": {"type": "array", "items": {"$ref": "#/components/schemas/ReglaVerificacion"}},
            "conciliacion": {"type": "object", "properties": {
                "coincidencia": {"type": "string", "enum": ["total", "parcial", "ninguna", "error", "no_aplica", "no_consultado"], "nullable": True},
                "detalle": {"type": "string", "nullable": True}, "intento": {"type": "integer", "nullable": True},
                "deposito": {"$ref": "#/components/schemas/Deposito"}}},
            "semaforo": {"type": "string", "enum": ["verde", "amarillo", "rojo"]},
            "justificacion": {"type": "string", "description": "Agente de Riesgo; si no es verde, empieza con el motivo determinista."},
            "ruta": {"type": "string", "enum": ["aprobar", "revision", "rechazar"]},
            "alerta_cumplimiento": {"type": "boolean", "description": "Monto ≥ umbral de registro UIF (referencial US$ 10,000)."},
            "monto_usd": {"type": "number"}, "motivo_sugerido": {"type": "string", "nullable": True},
            "numero_operacion": {"type": "string", "description": "N° leído del comprobante (detección de duplicados)."},
            "fecha_revision": {"type": "string", "format": "date-time"}, "fecha_fin": {"type": "string", "format": "date-time"},
            "estado_final": {"type": "string", "enum": ["En proceso", "Rechazada"]},
            "decision": {"type": "object", "properties": {
                "decision": {"type": "string", "enum": ["aprobar", "rechazar"]},
                "decidido_por": {"type": "string", "enum": ["agente", "operador"]},
                "motivo": {"type": "string", "nullable": True}, "fecha": {"type": "string", "format": "date-time"}}},
            "modelos": {"type": "object", "properties": {"vision": {"type": "string", "nullable": True}, "texto": {"type": "string", "nullable": True}}},
        },
    },
    "ValidacionesOperacionResponse": {
        "type": "object",
        "properties": {"id_operacion": {"type": "string"}, "total": {"type": "integer"},
                       "validaciones": {"type": "array", "items": {"$ref": "#/components/schemas/Validacion"}}},
    },
    "ValidacionesListResponse": {
        "type": "object",
        "properties": {"validaciones": {"type": "array", "items": {"$ref": "#/components/schemas/Validacion"}}, "total": {"type": "integer"}},
    },
    "DecisionRequest": {
        "type": "object", "required": ["decision"],
        "properties": {"decision": {"type": "string", "enum": ["aprobar", "rechazar"]},
                       "motivo": {"type": "string", "minLength": 3, "maxLength": 300, "description": "Obligatorio al rechazar."}},
    },
    "DecisionResponse": {
        "type": "object",
        "properties": {"mensaje": {"type": "string"}, "id_operacion": {"type": "string"}, "decision": {"type": "string", "enum": ["aprobar", "rechazar"]}},
    },
    "ReiniciarDemoRequest": {
        "type": "object",
        "properties": {
            "incluir_operaciones": {"type": "boolean", "default": False, "description": "También borra todas las operaciones y sus comprobantes en S3 (los clientes se conservan)."},
            "conservar_demo": {"type": "boolean", "default": True, "description": "El banco conserva los depósitos de los comprobantes de la demo web (origen_datos \"demo\"). false los borra también."},
        },
    },
    "ReiniciarDemoResponse": {
        "type": "object",
        "properties": {
            "mensaje": {"type": "string"}, "ejecuciones_detenidas": {"type": "integer"}, "validaciones_borradas": {"type": "integer"},
            "banco": {"$ref": "#/components/schemas/ReiniciarBancoResponse"},
            "operaciones": {"type": "object", "description": "Solo con incluir_operaciones.", "properties": {
                "operaciones_borradas": {"type": "integer"}, "comprobantes_borrados": {"type": "integer"}}},
        },
    },
    "Deposito": {
        "type": "object", "nullable": True,
        "properties": {
            "cuenta": {"type": "string", "description": "Cuenta de NexoCambio (solo dígitos)."},
            "mov": {"type": "string", "description": "<fecha>#<numero_operacion>"},
            "fecha": {"type": "string", "format": "date"}, "numero_operacion": {"type": "string"},
            "monto": {"type": "number"}, "moneda": {"type": "string", "enum": ["PEN", "USD", "EUR"]},
            "banco_origen": {"type": "string"}, "ordenante": {"type": "string"},
            "origen_datos": {"type": "string", "enum": ["semilla", "prueba", "demo"]},
            "registrado": {"type": "string", "format": "date-time"},
        },
    },
    "DepositoRequest": {
        "type": "object", "required": ["cuenta_destino", "monto", "moneda", "numero_operacion"],
        "properties": {
            "cuenta_destino": {"type": "string", "description": "Cuenta o CCI de NexoCambio tal como aparece en el comprobante (p. ej. «**** 0-39» o «CCI ****0039-14»)."},
            "monto": {"type": "number", "exclusiveMinimum": True, "minimum": 0}, "moneda": {"type": "string", "enum": ["PEN", "USD", "EUR"]},
            "numero_operacion": {"type": "string", "description": "Entre 4 y 20 dígitos."},
            "banco_origen": {"type": "string", "default": "BCP"}, "ordenante": {"type": "string", "default": "Cliente"},
            "fecha": {"type": "string", "format": "date", "description": "Por defecto, hoy."},
            "origen_datos": {"type": "string", "enum": ["prueba", "demo"], "default": "prueba",
                             "description": "\"demo\": depósito de un comprobante de la demo web; el reinicio lo conserva."},
        },
    },
    "DepositosListResponse": {
        "type": "object",
        "properties": {"depositos": {"type": "array", "items": {"$ref": "#/components/schemas/Deposito"}}, "total": {"type": "integer"}},
    },
    "ReiniciarBancoResponse": {
        "type": "object",
        "properties": {"borrados": {"type": "integer"}, "conservados": {"type": "integer", "description": "Depósitos de la demo conservados."},
                       "semilla": {"type": "integer", "description": "Depósitos históricos recargados (20)."}},
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
        "description": "Requiere JWT. JPG/PNG/WEBP/PDF, máx. 4 MB; el contenido real debe coincidir con el content_type declarado. Pasa el estado a 'Pendiente de validación' e inicia el workflow NexoGuard (StartExecution); el resultado se consulta en GET /validaciones/{id_operacion}.",
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
    # ------------------------------------------------------------------ NexoGuard: API Validaciones
    "/validaciones/{id_operacion}": {"get": {
        "tags": ["NexoGuard · Validaciones"], "summary": "Estado de la validación automática (vista del cliente)",
        "description": "Requiere JWT del dueño. El front la consulta cada 3 s mientras está en_curso y cada 10 s en revisión. "
                       "La operación conserva sus 4 estados; este es el subestado de NexoGuard.",
        "security": AUTH, "parameters": ID_OP,
        "responses": {
            "200": ok("Última validación de la operación.", "ValidacionCliente",
                      {"id_operacion": "NX-A1B2C3D4", "estado": "finalizada", "fecha_inicio": "2026-11-12T20:09:18.326Z",
                       "fecha_fin": "2026-11-12T20:09:27.900Z", "estado_final": "En proceso", "decidido_por": "agente", "motivo": None}),
            "401": SIN_TOKEN,
            "404": err(404, "La operación no tiene validaciones, o no te pertenece.", "sin_validacion"),
        },
    }},
    "/validaciones/{id_operacion}/admin": {"get": {
        "tags": ["NexoGuard · Back-office"], "summary": "Análisis completo de una operación (revisión asistida)",
        "description": "x-admin-key. Todas las validaciones de la operación, la más reciente primero: datos leídos por la IA, "
                       "verificaciones, conciliación con el banco, semáforo, justificación y decisión.",
        "security": ADMIN, "parameters": ID_OP,
        "responses": {
            "200": ok("Validaciones de la operación.", "ValidacionesOperacionResponse"),
            "403": SIN_ADMIN,
            "404": err(404, "La operación no tiene validaciones registradas.", "sin_validacion"),
        },
    }},
    "/validaciones/admin": {"get": {
        "tags": ["NexoGuard · Back-office"], "summary": "Cola de revisión de NexoGuard",
        "description": "x-admin-key. Por defecto los casos en_revision, el más antiguo primero (máx. 200); finalizada, el más reciente primero.",
        "security": ADMIN,
        "parameters": [{"name": "estado", "in": "query", "required": False,
                        "schema": {"type": "string", "enum": ESTADOS_VALIDACION, "default": "en_revision"}}],
        "responses": {
            "200": ok("Validaciones en ese estado.", "ValidacionesListResponse"),
            "400": err(400, "Estado no válido.", "estado_invalido"),
            "403": SIN_ADMIN,
        },
    }},
    "/validaciones/{id_operacion}/decision": {"post": {
        "tags": ["NexoGuard · Back-office"], "summary": "Decisión del operador (reanuda el workflow)",
        "description": "x-admin-key. Solo si la validación está en_revision. Llama a SendTaskSuccess con el token guardado; "
                       "el workflow aplica la decisión y la operación cambia de estado en unos segundos.",
        "security": ADMIN, "parameters": ID_OP,
        "requestBody": cuerpo("DecisionRequest", {"decision": "rechazar", "motivo": "El monto transferido no coincide con la operación."}),
        "responses": {
            "202": ok("Decisión registrada.", "DecisionResponse"),
            "400": err(400, "Decisión inválida, o falta el motivo al rechazar.", "decision_invalida", "longitud_invalida", "cuerpo_vacio", "json_invalido"),
            "403": SIN_ADMIN,
            "409": err(409, "La operación no espera revisión, u otro operador ya decidió.", "sin_revision_pendiente", "ya_decidida"),
            "410": err(410, "La revisión venció (72 h).", "revision_vencida"),
            "502": err(502, "Step Functions no respondió; se puede reintentar.", "servicio_no_disponible"),
        },
    }},
    "/demo/reiniciar": {"post": {
        "tags": ["NexoGuard · Back-office"], "summary": "Reiniciar los datos de prueba",
        "description": "x-admin-key. Entorno académico: detiene las ejecuciones en curso, vacía nexo-validaciones (el control de "
                       "duplicados), reinicia el banco simulado y, con incluir_operaciones, borra operaciones y comprobantes. "
                       "Por defecto conserva los depósitos de la demo web. También disponible como botón en el back-office.",
        "security": ADMIN,
        "requestBody": {"required": False, "content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/ReiniciarDemoRequest"}, "example": {"incluir_operaciones": True}}}},
        "responses": {
            "200": ok("Datos reiniciados.", "ReiniciarDemoResponse",
                      {"mensaje": "Datos de prueba reiniciados.", "ejecuciones_detenidas": 0, "validaciones_borradas": 9,
                       "banco": {"borrados": 20, "conservados": 5, "semilla": 20},
                       "operaciones": {"operaciones_borradas": 3, "comprobantes_borrados": 3}}),
            "403": SIN_ADMIN,
        },
    }},
    # ------------------------------------------------------------------ Banco simulado (sistema externo)
    "/banco/depositos": {
        "post": {
            "tags": ["Banco simulado (externo)"], "summary": "Registrar un depósito («el cliente transfirió»)",
            "description": "x-banco-key. Simula la API de movimientos de un banco; NexoGuard la consulta por HTTPS para conciliar.",
            "security": BANCO,
            "requestBody": cuerpo("DepositoRequest", {"cuenta_destino": "**** 0-39", "monto": 1000, "moneda": "PEN",
                                                      "numero_operacion": "04417483", "banco_origen": "BCP",
                                                      "ordenante": "Lucía Ramírez Torres", "fecha": "2026-11-12", "origen_datos": "demo"}),
            "responses": {
                "201": ok("Depósito registrado.", "Deposito"),
                "400": err(400, "Cuerpo inválido.", "cuerpo_vacio", "json_invalido", "longitud_invalida"),
                "403": SIN_BANCO,
                "409": err(409, "Ese depósito ya está registrado.", "duplicado"),
                "422": err(422, "Dato fuera de regla.", "moneda_invalida", "cuenta_invalida", "numero_invalido", "monto_invalido"),
            },
        },
        "get": {
            "tags": ["Banco simulado (externo)"], "summary": "Consultar depósitos",
            "description": "x-banco-key. Por número de operación, o por cuenta y fecha.",
            "security": BANCO,
            "parameters": [
                {"name": "numero_operacion", "in": "query", "required": False, "schema": {"type": "string"}},
                {"name": "cuenta", "in": "query", "required": False, "schema": {"type": "string"}},
                {"name": "fecha", "in": "query", "required": False, "schema": {"type": "string", "format": "date"}},
            ],
            "responses": {
                "200": ok("Depósitos encontrados (lista vacía si no hay).", "DepositosListResponse"),
                "400": err(400, "Indica numero_operacion, o cuenta y fecha.", "parametros_faltantes"),
                "403": SIN_BANCO,
            },
        },
    },
    "/banco/reiniciar": {"post": {
        "tags": ["Banco simulado (externo)"], "summary": "Reiniciar el banco simulado",
        "description": "x-banco-key. Borra los depósitos de prueba y recarga 20 depósitos históricos (semilla). "
                       "Conserva los de la demo web salvo conservar_demo: false. Lo invoca POST /demo/reiniciar.",
        "security": BANCO,
        "requestBody": {"required": False, "content": {"application/json": {
            "schema": {"type": "object", "properties": {"conservar_demo": {"type": "boolean", "default": True}}},
            "example": {"conservar_demo": True}}}},
        "responses": {
            "200": ok("Banco reiniciado.", "ReiniciarBancoResponse", {"borrados": 20, "conservados": 5, "semilla": 20}),
            "403": SIN_BANCO,
        },
    }},
}

OPENAPI = {
    "openapi": "3.0.3",
    "info": {
        "title": "NexoCambio API",
        "version": "2.0.0",
        "description": (
            "Casa de cambio de divisas y cripto — API serverless (API Gateway HTTP API + Lambdas + DynamoDB + S3).\n\n"
            "Microservicios: Cotizaciones, Clientes, Operaciones y **Validaciones (NexoGuard)**, más el **banco simulado**, "
            "un sistema externo con su propia clave. NexoGuard es el workflow agéntico de Step Functions que valida cada "
            "comprobante: se inicia al adjuntarlo (POST /operaciones/{id}/comprobante) y su resultado se consulta en "
            "/validaciones.\n\n"
            "Formato JSON. Los errores siempre devuelven `{mensaje, codigo}`. Las rutas de cliente van con "
            "`Authorization: Bearer <token>` (JWT HS256, ver POST /login); las de back-office simulado van con la "
            "cabecera `x-admin-key` en vez de JWT; las del banco simulado, con `x-banco-key`. Si una ruta protegida "
            "responde 401, el front limpia la sesión y redirige a login.\n\n"
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
        {"name": "NexoGuard · Validaciones", "description": "Subestado de la validación automática, para el cliente."},
        {"name": "NexoGuard · Back-office", "description": "Cola de revisión, análisis del agente, decisión del operador y reinicio de datos de prueba."},
        {"name": "Banco simulado (externo)", "description": "API bancaria simulada que NexoGuard consulta para conciliar depósitos."},
    ],
    "components": {
        "securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
            "adminKey": {"type": "apiKey", "in": "header", "name": "x-admin-key"},
            "bancoKey": {"type": "apiKey", "in": "header", "name": "x-banco-key"},
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

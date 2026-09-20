"""
nexo_common — utilidades compartidas por los microservicios de NexoCambio.

Se despliega como AWS Lambda Layer para que cada microservicio siga siendo
independiente (su propio código, su propia base de datos) sin duplicar código
transversal: respuestas HTTP, autenticación JWT, hash de contraseñas y logging.

Solo usa la librería estándar de Python + boto3 (incluido en el runtime de
Lambda), por lo que no requiere empaquetar dependencias.
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from datetime import datetime, timezone
from decimal import Decimal

logger = logging.getLogger("nexo")
logger.setLevel(logging.INFO)

ALFABETO_ID = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O/1/I para evitar confusiones


# --------------------------------------------------------------------------
# Errores y respuestas HTTP
# --------------------------------------------------------------------------
class ApiError(Exception):
    """Error de negocio/validación que se traduce a una respuesta HTTP."""

    def __init__(self, status: int, mensaje: str, codigo: str = "error"):
        super().__init__(mensaje)
        self.status = status
        self.mensaje = mensaje
        self.codigo = codigo


def _json_default(o):
    if isinstance(o, Decimal):
        # enteros como int; decimales como float (suficiente para montos de este MVP)
        return int(o) if o == o.to_integral_value() else float(o)
    raise TypeError(f"No serializable: {type(o)}")


def respuesta(status: int, cuerpo) -> dict:
    """Respuesta compatible con API Gateway HTTP API (payload 2.0).
    Los encabezados CORS los agrega API Gateway (CorsConfiguration)."""
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(cuerpo, default=_json_default, ensure_ascii=False),
    }


def log(evento: str, **datos):
    """Log estructurado (JSON) → CloudWatch Logs. Nunca registrar datos sensibles."""
    logger.info(json.dumps({"evento": evento, **datos}, default=str, ensure_ascii=False))


def manejar(rutas: dict):
    """Crea el `handler` de una Lambda a partir de una tabla de rutas.

    rutas = {"POST /cotizar": funcion, ...}. Cada función recibe (event) y
    devuelve (status, cuerpo). Cualquier ApiError se convierte en JSON con
    {"mensaje", "codigo"}; los errores no controlados devuelven 500 sin filtrar
    detalles internos.
    """

    def handler(event, context=None):
        ruta = event.get("routeKey", "?")
        try:
            fn = rutas.get(ruta)
            if fn is None:
                raise ApiError(404, "Recurso no encontrado.", "no_encontrado")
            status, cuerpo = fn(event)
            return respuesta(status, cuerpo)
        except ApiError as e:
            log("api_error", ruta=ruta, status=e.status, codigo=e.codigo)
            return respuesta(e.status, {"mensaje": e.mensaje, "codigo": e.codigo})
        except Exception:  # noqa: BLE001
            logger.exception("error_no_controlado ruta=%s", ruta)
            return respuesta(500, {"mensaje": "Error interno. Inténtalo nuevamente.", "codigo": "error_interno"})

    return handler


# --------------------------------------------------------------------------
# Entrada
# --------------------------------------------------------------------------
def cuerpo_json(event) -> dict:
    raw = event.get("body")
    if raw is None or raw == "":
        raise ApiError(400, "El cuerpo de la solicitud es obligatorio.", "cuerpo_vacio")
    if event.get("isBase64Encoded"):
        try:
            raw = base64.b64decode(raw).decode("utf-8")
        except Exception:  # noqa: BLE001
            raise ApiError(400, "Cuerpo de la solicitud inválido.", "cuerpo_invalido")
    try:
        data = json.loads(raw, parse_float=Decimal)
    except (ValueError, TypeError):
        raise ApiError(400, "El cuerpo debe ser un JSON válido.", "json_invalido")
    if not isinstance(data, dict):
        raise ApiError(400, "El cuerpo debe ser un objeto JSON.", "json_invalido")
    return data


def encabezado(event, nombre: str):
    """HTTP API entrega los encabezados en minúsculas."""
    return (event.get("headers") or {}).get(nombre.lower())


def parametro_ruta(event, nombre: str) -> str:
    valor = (event.get("pathParameters") or {}).get(nombre)
    if not valor:
        raise ApiError(400, f"Falta el parámetro {nombre}.", "parametro_faltante")
    return valor


def requeridos(datos: dict, campos):
    faltan = [c for c in campos if datos.get(c) in (None, "")]
    if faltan:
        raise ApiError(400, "Faltan campos obligatorios: " + ", ".join(faltan) + ".", "campos_faltantes")


def texto(valor, campo: str, minimo=1, maximo=120) -> str:
    if not isinstance(valor, str):
        raise ApiError(400, f"El campo {campo} debe ser texto.", "tipo_invalido")
    v = valor.strip()
    if not (minimo <= len(v) <= maximo):
        raise ApiError(400, f"El campo {campo} debe tener entre {minimo} y {maximo} caracteres.", "longitud_invalida")
    return v


# --------------------------------------------------------------------------
# Identificadores y fechas
# --------------------------------------------------------------------------
def nuevo_id(prefijo: str, n: int = 8) -> str:
    return prefijo + "".join(secrets.choice(ALFABETO_ID) for _ in range(n))


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


# --------------------------------------------------------------------------
# Contraseñas (PBKDF2-HMAC-SHA256, librería estándar)
# --------------------------------------------------------------------------
def _iteraciones() -> int:
    return int(os.environ.get("PBKDF2_ITER", "200000"))


def hash_password(password: str) -> str:
    sal = secrets.token_hex(16)
    it = _iteraciones()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal), it)
    return f"pbkdf2_sha256${it}${sal}${dk.hex()}"


def verificar_password(password: str, almacenado: str) -> bool:
    try:
        alg, it, sal, esperado = almacenado.split("$")
        if alg != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal), int(it))
        return hmac.compare_digest(dk.hex(), esperado)
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------------------
# JWT HS256 (sin dependencias externas)
# --------------------------------------------------------------------------
def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _firma(mensaje: str, secreto: str) -> str:
    return _b64e(hmac.new(secreto.encode(), mensaje.encode(), hashlib.sha256).digest())


def jwt_crear(claims: dict, secreto: str, ttl_seg: int = 7200) -> str:
    ahora_s = int(time.time())
    cuerpo = {**claims, "iat": ahora_s, "exp": ahora_s + ttl_seg}
    h = _b64e(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    p = _b64e(json.dumps(cuerpo, separators=(",", ":")).encode())
    return f"{h}.{p}.{_firma(h + '.' + p, secreto)}"


def jwt_validar(token: str, secreto: str) -> dict:
    try:
        h, p, f = token.split(".")
        if not hmac.compare_digest(f, _firma(h + "." + p, secreto)):
            raise ValueError("firma")
        if json.loads(_b64d(h)).get("alg") != "HS256":
            raise ValueError("alg")
        claims = json.loads(_b64d(p))
        if int(claims["exp"]) < int(time.time()):
            raise ApiError(401, "Tu sesión expiró. Inicia sesión otra vez.", "sesion_expirada")
        return claims
    except ApiError:
        raise
    except Exception:  # noqa: BLE001
        raise ApiError(401, "Token inválido. Inicia sesión otra vez.", "token_invalido")


def exigir_sesion(event) -> dict:
    """Valida `Authorization: Bearer <jwt>` y devuelve los claims (sub = id_cliente)."""
    auth = encabezado(event, "authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise ApiError(401, "Debes iniciar sesión para continuar.", "no_autenticado")
    secreto = os.environ.get("JWT_SECRET", "")
    if not secreto:
        raise ApiError(500, "Configuración de seguridad incompleta.", "config")
    return jwt_validar(auth[7:].strip(), secreto)


# --------------------------------------------------------------------------
# Validaciones de negocio reutilizables
# --------------------------------------------------------------------------
RE_CORREO = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
RE_CELULAR = re.compile(r"^9\d{8}$")
RE_RUC = re.compile(r"^(10|15|17|20)\d{9}$")


def validar_documento(tipo: str, numero: str, campo="numero_documento"):
    reglas = {
        "DNI": (r"^\d{8}$", "El DNI tiene 8 dígitos."),
        "CE": (r"^[A-Za-z0-9]{9,12}$", "El carné de extranjería tiene entre 9 y 12 caracteres."),
        "Pasaporte": (r"^[A-Za-z0-9]{6,12}$", "Revisa el número de pasaporte."),
        "RUC": (r"^(10|15|17|20)\d{9}$", "El RUC tiene 11 dígitos y empieza con 10 o 20."),
    }
    if tipo not in reglas:
        raise ApiError(400, "Tipo de documento no válido.", "documento_invalido")
    patron, msg = reglas[tipo]
    if not re.match(patron, numero or ""):
        raise ApiError(400, msg, "documento_invalido")


def validar_password(pw: str):
    if not isinstance(pw, str) or len(pw) < 8 or not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        raise ApiError(400, "Usa al menos 8 caracteres, con letras y números.", "password_debil")

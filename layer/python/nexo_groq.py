"""
nexo_groq — cliente mínimo de la API de Groq (compatible con OpenAI) para los agentes de NexoGuard.

Sin memoria: cada llamada envía todo su contexto. Solo librería estándar (urllib).
Los nombres de las excepciones son los que captura el Retry de Step Functions:
  GroqLimite  → 429 (límite de tokens/solicitudes por minuto): reintentar con espera
  GroqError   → cualquier otro fallo de la API o respuesta no interpretable
"""
import json
import os
import urllib.error
import urllib.request

URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqLimite(Exception):
    pass


class GroqError(Exception):
    pass


def chat_json(modelo: str, contenido, timeout: int = 45, max_tokens: int = 1024, **extra) -> dict:
    """Envía un mensaje de usuario (texto o lista multimodal) y devuelve el JSON que responde el modelo.
    `extra`: parámetros adicionales de la API (p. ej. reasoning_effort para modelos de razonamiento)."""
    clave = os.environ.get("GROQ_API_KEY", "")
    if not clave:
        raise GroqError("GROQ_API_KEY no configurada")
    cuerpo = {"model": modelo, "temperature": 0, "max_tokens": max_tokens,
              "response_format": {"type": "json_object"},
              "messages": [{"role": "user", "content": contenido}], **extra}
    req = urllib.request.Request(URL, data=json.dumps(cuerpo).encode(), headers={
        "Authorization": f"Bearer {clave}", "Content-Type": "application/json", "User-Agent": "nexoguard/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        detalle = e.read().decode(errors="replace")[:300]
        if e.code == 429:
            raise GroqLimite(detalle)
        raise GroqError(f"HTTP {e.code}: {detalle}")
    except (urllib.error.URLError, TimeoutError) as e:
        raise GroqError(f"Sin respuesta de Groq: {e}")
    try:
        return json.loads(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, ValueError, TypeError):
        raise GroqError("Respuesta de Groq no es un JSON válido")

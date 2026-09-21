#!/usr/bin/env python3
"""Genera public/config.json con la URL de la API para el build de Angular.

Uso:  python scripts/configurar_front.py <salida_config.json> <URL_API>
Ejemplo de URL: https://abc123.execute-api.us-east-1.amazonaws.com/v1
"""
import json
import sys

if len(sys.argv) != 3:
    sys.exit(__doc__)
salida, url = sys.argv[1:]
url = url.rstrip("/")
with open(salida, "w", encoding="utf-8") as f:
    json.dump({"apiBaseUrl": url}, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"config.json generado con apiBaseUrl={url} -> {salida}")

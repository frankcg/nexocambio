#!/usr/bin/env python3
"""Inyecta la URL de la API en CONFIG.API del frontend (index.html).

Uso:  python scripts/configurar_front.py <index.html> <salida.html> <URL_API>
Ejemplo de URL: https://abc123.execute-api.us-east-1.amazonaws.com/v1
"""
import re
import sys

if len(sys.argv) != 4:
    sys.exit(__doc__)
origen, salida, url = sys.argv[1:]
url = url.rstrip("/")
html = open(origen, encoding="utf-8").read()
total = 0
for servicio in ("cotizaciones", "clientes", "operaciones"):
    html, n = re.subn(rf'({servicio}:\s*)"[^"]*"', rf'\g<1>"{url}"', html, count=1)
    total += n
if total != 3:
    sys.exit(f"No se encontró CONFIG.API completo en {origen} (reemplazos: {total}/3).")
open(salida, "w", encoding="utf-8").write(html)
print(f"Frontend configurado con API {url} → {salida}")

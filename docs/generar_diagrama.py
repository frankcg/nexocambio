#!/usr/bin/env python3
"""Genera docs/arquitectura_nexocambio.svg/.png (requiere cairosvg)."""
from xml.sax.saxutils import escape as esc

W, H = 1600, 980
out = []
def a(s): out.append(s)

COL = {"lambda": "#ED7100", "api": "#8C4FFF", "ddb": "#3B48CC", "s3": "#3F8624", "cw": "#E7157B", "ext": "#5B6B85", "user": "#232F3E"}
FONT = "DejaVu Sans, Verdana, Segoe UI Symbol, sans-serif"

def text(x, y, s, size=13, bold=False, fill="#232F3E", anchor="start", italic=False, halo=False):
    a(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"'
      f'{" font-weight=\"700\"" if bold else ""}{" font-style=\"italic\"" if italic else ""}'
      f'{" stroke=\"#fff\" stroke-width=\"4\" stroke-linejoin=\"round\" paint-order=\"stroke\"" if halo else ""}>{esc(s)}</text>')

def num(n, x, y):
    a(f'<circle cx="{x}" cy="{y - 4}" r="8" fill="#232F3E"/>')
    text(x, y - 0.5, str(n), 10, True, "#fff", "middle")


def box(x, y, w, h, kind, glyph, titulo, lineas=(), dash=False, tsize=14):
    c = COL[kind]
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#fff" stroke="{c}" stroke-width="2"'
      f'{" stroke-dasharray=\"6 5\"" if dash else ""}/>')
    a(f'<rect x="{x+10}" y="{y+10}" width="42" height="42" rx="8" fill="{c}"/>')
    text(x + 31, y + 39, glyph, 18, True, "#fff", "middle")
    text(x + 62, y + 28, titulo, tsize, True)
    for i, l in enumerate(lineas):
        text(x + 62, y + 46 + i * 16, l, 11.5, fill="#4A5568")

def flecha(d, color="#232F3E", dash=False, label=None, lx=0, ly=0, marker=True, w=2, halo=False):
    a(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}"{" stroke-dasharray=\"6 5\"" if dash else ""}'
      f'{" marker-end=\"url(#f)\"" if marker else ""}/>')
    if label:
        text(lx, ly, label, 11, False, color, "middle", True, halo)

a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
a('<defs><marker id="f" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
  '<path d="M0,0 L10,5 L0,10 z" fill="#232F3E"/></marker></defs>')
a(f'<rect width="{W}" height="{H}" fill="#F7F9FC"/>')
text(W / 2, 44, "Arquitectura AWS del MVP — NexoCambio", 30, True, "#0E1B33", "middle")
text(W / 2, 72, "Microservicios serverless · AWS Academy Learner Lab · Región us-east-1 (N. Virginia)", 15, False, "#4A5568", "middle")

# Región
a('<rect x="190" y="98" width="1385" height="820" rx="14" fill="#fff" stroke="#232F3E" stroke-width="1.5" stroke-dasharray="2 0"/>')
text(206, 121, "AWS Cloud — us-east-1", 13, True)

# Usuario
a(f'<rect x="20" y="395" width="140" height="130" rx="12" fill="#fff" stroke="{COL["user"]}" stroke-width="2"/>')
a(f'<circle cx="90" cy="435" r="17" fill="{COL["user"]}"/><rect x="66" y="456" width="48" height="22" rx="10" fill="{COL["user"]}"/>')
text(90, 498, "Cliente web", 13, True, anchor="middle"); text(90, 514, "desktop · móvil", 11, False, "#4A5568", "middle")

# Operador de back-office
a(f'<rect x="20" y="580" width="140" height="105" rx="12" fill="#fff" stroke="{COL["user"]}" stroke-width="2"/>')
a(f'<circle cx="90" cy="603" r="13" fill="{COL["user"]}"/><rect x="72" y="619" width="36" height="16" rx="8" fill="{COL["user"]}"/>')
text(90, 655, "Back-office", 13, True, anchor="middle"); text(90, 671, "/admin · x-admin-key", 11, False, "#4A5568", "middle")

# Frontend + API
box(225, 150, 230, 118, "s3", "S3", "S3 — Sitio web", ["Frontend Angular (SPA)", "Cotizador · operar · login", "registro · mis operaciones", "Back-office en /#/admin", "Servido por HTTPS"], tsize=14)
box(225, 385, 230, 130, "api", "API", "API Gateway", ["HTTP API · stage v1", "CORS · throttling", "11 rutas → 3 Lambdas"], tsize=14)
flecha("M112,395 L112,210 L225,210")
num(1, 96, 200); text(108, 200, "HTTPS (Angular)", 11, False, "#232F3E", "start", True)
flecha("M160,460 L225,450")
num(2, 132, 548); text(144, 548, "HTTPS + JSON + JWT", 11, False, "#232F3E", "start", True)
flecha("M160,632 L300,632 L300,515")
num(4, 316, 545); text(328, 545, "HTTPS + JSON", 11, False, "#232F3E", "start", True)
text(328, 559, "+ x-admin-key", 11, False, "#232F3E", "start", True)

# Cómputo
a('<rect x="560" y="132" width="290" height="700" rx="12" fill="#FFF6EC" stroke="#ED7100" stroke-width="1.5" stroke-dasharray="7 5"/>')
text(575, 154, "Cómputo — AWS Lambda (Python 3.12)", 12.5, True, "#B45309")
box(585, 175, 240, 118, "lambda", "λ", "Cotizaciones", ["POST /cotizar", "Tasa, monto, vigencia 5 min", "Tasas en vivo con caché"])
box(585, 385, 240, 130, "lambda", "λ", "Operaciones", ["POST/GET /operaciones", "POST …/comprobante", "Back-office (x-admin-key):", "GET …/admin, …/{id}/admin", "PATCH …/{id}/estado"])
box(585, 600, 240, 118, "lambda", "λ", "Clientes / Auth", ["POST /registro · POST /login", "GET /clientes/{id}", "PBKDF2 + JWT HS256"])
a('<rect x="585" y="740" width="240" height="66" rx="8" fill="#fff" stroke="#ED7100" stroke-width="1.5" stroke-dasharray="4 3"/>')
text(597, 762, "Lambda Layer: nexo_common", 12, True, "#B45309"); text(597, 780, "JWT · hash · validaciones · respuestas", 11, fill="#4A5568")
text(597, 796, "Rol de ejecución: LabRole (Learner Lab)", 11, fill="#4A5568")

# API → Lambdas
flecha("M455,450 L520,450 L520,234 L585,234")
num(3, 520, 344)
flecha("M455,450 L585,450", marker=True)
flecha("M455,450 L520,450 L520,659 L585,659")
# Invocación interna
flecha("M705,385 L705,293", "#B45309", w=2.2)
text(715, 336, "Lambda Invoke:", 11, False, "#B45309", "start", True)
text(715, 350, "obtener cotización", 11, False, "#B45309", "start", True)

# Datos
box(985, 150, 250, 60, "ddb", "DB", "nexo-tasas", ["PK moneda"], tsize=13.5)
box(985, 222, 250, 76, "ddb", "DB", "nexo-cotizaciones", ["PK id_cotizacion", "TTL: se auto-elimina"], tsize=13.5)
box(985, 372, 250, 92, "ddb", "DB", "nexo-operaciones", ["PK id_operacion", "GSI cliente-fecha-index", "Scan (listado back-office)"], tsize=13.5)
box(985, 476, 250, 76, "s3", "S3", "S3 comprobantes", ["Privado · cifrado AES-256", "URL temporal firmada"], tsize=13.5)
box(985, 615, 250, 90, "ddb", "DB", "nexo-clientes", ["pk = CLI# · EMAIL# · DOC#", "Unicidad por transacción"], tsize=13.5)
flecha("M825,215 L985,180"); flecha("M825,250 L985,260")
flecha("M825,420 L985,410"); flecha("M825,480 L985,500")
flecha("M825,660 L985,660")
text(1110, 138, "BD del microservicio Cotizaciones", 11, False, "#3B48CC", "middle", True)
text(1110, 360, "BD y archivos del microservicio Operaciones", 11, False, "#3B48CC", "middle", True)
text(1110, 603, "BD del microservicio Clientes", 11, False, "#3B48CC", "middle", True)

# Fuente externa
box(1290, 150, 265, 118, "ext", "↗", "APIs públicas de tasas", ["FX (PEN/EUR) y cripto", "(BTC, ETH, USDT, USDC)", "Vía internet · 1 consulta/5 min"], dash=True)
flecha("M825,185 L900,185 L900,118 L1422,118 L1422,150", "#5B6B85", dash=True, label="HTTPS (opcional; con caché en DynamoDB)", lx=1160, ly=112)

# Monitoreo
box(985, 760, 250, 100, "cw", "CW", "CloudWatch", ["Logs (14 días) · métricas", "Alarmas: errores Lambda", "y 5xx de la API"], tsize=13.5)
box(1290, 760, 265, 100, "cw", "SNS", "SNS — alertas", ["Notificación por correo", "cuando salta una alarma"], tsize=13.5)
flecha("M825,790 L985,805", "#E7157B", dash=True)
flecha("M1235,810 L1290,810", "#E7157B", dash=True)
flecha("M430,515 L430,880 L985,880 L985,850", "#E7157B", dash=True, label="métricas de la API", lx=660, ly=872)

# Notas
a('<rect x="1290" y="300" width="265" height="440" rx="10" fill="#F0F5FF" stroke="#3B48CC" stroke-width="1.2"/>')
text(1305, 324, "Decisiones de diseño", 13.5, True, "#3B48CC")
notas = ["• Cada microservicio tiene su", "  propia base de datos.", "• Operaciones NO confía en la tasa", "  del navegador: la valida con", "  Cotizaciones (Lambda→Lambda).",
         "• Contraseñas con PBKDF2;", "  sesión con JWT (2 h).", "• Back-office (/admin): clave", "  compartida x-admin-key en vez", "  de JWT; aprueba o rechaza.",
         "• Comprobantes: bucket privado,", "  validación de formato real y", "  enlaces temporales.",
         "• Pago por uso: sin servidores", "  encendidos 24×7.", "• Frontend Angular en S3, por", "  HTTPS (endpoint REST de S3)."]
for i, n in enumerate(notas):
    text(1305, 348 + i * 20, n, 12, fill="#232F3E")

# Opcional
a('<rect x="20" y="705" width="150" height="200" rx="10" fill="#fff" stroke="#8A94A6" stroke-width="1.4" stroke-dasharray="6 5"/>')
text(95, 729, "Opcional / fuera del", 11.5, True, "#5B6B85", "middle"); text(95, 745, "Learner Lab:", 11.5, True, "#5B6B85", "middle")
for i, l in enumerate(["CloudFront (caché;", "el Lab lo deniega)", "", "Cognito (usuarios y", "roles reales)", "", "EventBridge + SES", "(avisos de estado)"]):
    text(30, 773 + i * 17, l, 11, fill="#4A5568")
text(W / 2, 950, "Flujo MVP: cotizar → registrarse / iniciar sesión → registrar operación → adjuntar comprobante → back-office aprueba o rechaza → consultar estado", 13, True, "#0E1B33", "middle")
a('</svg>')
open("docs/arquitectura_nexocambio.svg", "w", encoding="utf-8").write("\n".join(out))
import cairosvg
cairosvg.svg2png(url="docs/arquitectura_nexocambio.svg", write_to="docs/arquitectura_nexocambio.png", scale=2)
print("ok")

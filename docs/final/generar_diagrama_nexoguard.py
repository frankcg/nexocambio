#!/usr/bin/env python3
"""Genera docs/final/arquitectura_nexoguard.svg (y .png con Chrome/Edge headless si está disponible).
Mismo estilo que docs/generar_diagrama.py: cajas con insignia de color + sigla, sin iconos oficiales."""
import shutil
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape as esc

W, H = 1800, 1010
DIR = Path(__file__).resolve().parent
COL = {"lambda": "#ED7100", "api": "#8C4FFF", "ddb": "#3B48CC", "s3": "#3F8624", "cw": "#E7157B",
       "ext": "#5B6B85", "user": "#232F3E", "sfn": "#CD2264", "sns": "#E7157B"}
NUEVO = "#12A150"
FONT = "Segoe UI, DejaVu Sans, Verdana, sans-serif"
out = []


def a(s):
    out.append(s)


def text(x, y, s, size=13, bold=False, fill="#232F3E", anchor="start", halo=False):
    a(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"'
      f'{" font-weight=\"700\"" if bold else ""}'
      f'{" stroke=\"#fff\" stroke-width=\"4\" stroke-linejoin=\"round\" paint-order=\"stroke\"" if halo else ""}>{esc(s)}</text>')


def box(x, y, w, h, kind, glyph, titulo, lineas=(), nuevo=False, dash=False):
    c = COL[kind]
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#fff" stroke="{NUEVO if nuevo else c}" '
      f'stroke-width="{2.6 if nuevo else 2}"{" stroke-dasharray=\"6 5\"" if dash else ""}/>')
    a(f'<rect x="{x + 10}" y="{y + 10}" width="38" height="38" rx="8" fill="{c}"/>')
    text(x + 29, y + 35, glyph, 15, True, "#fff", "middle")
    text(x + 58, y + 27, titulo, 14, True)
    for i, l in enumerate(lineas):
        text(x + 58, y + 45 + i * 16, l, 11.5, fill="#4A5568")
    if nuevo:
        a(f'<rect x="{x + w - 54}" y="{y - 9}" width="50" height="18" rx="9" fill="{NUEVO}"/>')
        text(x + w - 29, y + 4, "NUEVO", 10, True, "#fff", "middle")


def paso(x, y, w, h, titulo, sub="", kind="lambda", glyph="λ"):
    c = COL[kind]
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#FFF7FA" stroke="{c}" stroke-width="1.6"/>')
    a(f'<rect x="{x + 6}" y="{y + 6}" width="24" height="{h - 12}" rx="5" fill="{c}"/>')
    text(x + 18, y + h / 2 + 5, glyph, 12, True, "#fff", "middle")
    text(x + 38, y + (19 if sub else h / 2 + 5), titulo, 12.5, True)
    if sub:
        text(x + 38, y + 35, sub, 10.5, fill="#4A5568")


def flecha(puntos, color="#232F3E", label="", lx=None, ly=None, dash=False, w=1.8, lsize=11):
    d = "M " + " L ".join(f"{px} {py}" for px, py in puntos)
    mid = "m" + color.strip("#")
    a(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}"{" stroke-dasharray=\"6 4\"" if dash else ""} '
      f'marker-end="url(#{mid})"/>')
    if label:
        (x1, y1), (x2, y2) = puntos[0], puntos[1]
        text(lx if lx is not None else (x1 + x2) / 2, ly if ly is not None else (y1 + y2) / 2 - 6, label, lsize,
             fill=color, anchor="middle", halo=True)


colores_flecha = {"#232F3E", COL["sfn"], COL["ext"], NUEVO, COL["sns"], COL["ddb"], COL["s3"]}
a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><defs>')
for c in colores_flecha:
    a(f'<marker id="m{c.strip("#")}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
      f'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{c}"/></marker>')
a('</defs>')
a(f'<rect width="{W}" height="{H}" fill="#fff"/>')
text(W / 2, 38, "Arquitectura AWS — NexoCambio + NexoGuard (workflow agéntico Nivel 4)", 24, True, "#0E1B33", "middle")
text(W / 2, 62, "Serverless · AWS Academy Learner Lab · Región us-east-1 (N. Virginia) · Stack en CloudFormation · rol LabRole",
     13, fill="#4A5568", anchor="middle")

# Nube AWS
a('<rect x="200" y="84" width="1370" height="830" rx="14" fill="none" stroke="#232F3E" stroke-width="1.6"/>')
text(216, 106, "AWS Cloud — us-east-1", 13, True)

# ---------------------------------------------------------------- usuarios
for y, t, s in [(150, "Cliente web", "desktop · móvil"), (455, "Back-office", "/admin · x-admin-key"),
                (790, "Oficial de", "cumplimiento (correo)")]:
    a(f'<rect x="24" y="{y}" width="150" height="104" rx="10" fill="#fff" stroke="#232F3E" stroke-width="2"/>')
    a(f'<circle cx="99" cy="{y + 30}" r="14" fill="#232F3E"/><path d="M73 {y + 70} Q99 {y + 38} 125 {y + 70} Z" fill="#232F3E"/>')
    text(99, y + 86, t, 13, True, anchor="middle")
    text(99, y + 100, s, 10.5, fill="#4A5568", anchor="middle")

# ---------------------------------------------------------------- borde
box(225, 125, 215, 90, "s3", "S3", "S3 — Sitio web", ["Angular (SPA) cliente", "y back-office", "+ estados NexoGuard"])
box(225, 330, 215, 140, "api", "API", "API Gateway", ["HTTP API · stage v1", "CORS · throttling", "11 rutas + 4 rutas", "/validaciones (nuevas)"])

# ---------------------------------------------------------------- microservicios
a('<rect x="470" y="110" width="470" height="440" rx="12" fill="#FFF8F1" stroke="#ED7100" stroke-dasharray="6 5" stroke-width="1.4"/>')
text(486, 132, "Microservicios del Proyecto Parcial (AWS Lambda · Python 3.12)", 12, True, "#ED7100")
box(486, 146, 200, 84, "lambda", "λ", "Cotizaciones", ["POST /cotizar"])
box(486, 254, 200, 84, "lambda", "λ", "Clientes / Auth", ["registro · login · JWT"])
box(486, 362, 200, 160, "lambda", "λ", "Operaciones", ["CRUD de operaciones", "back-office", "+ inicia NexoGuard", "  (StartExecution)", "+ aplicar_decision", "  (invoke interno)"], nuevo=False)
box(730, 146, 196, 70, "ddb", "DB", "nexo-tasas", ["nexo-cotizaciones"])
box(730, 254, 196, 70, "ddb", "DB", "nexo-clientes")
box(730, 362, 196, 70, "ddb", "DB", "nexo-operaciones")
box(730, 450, 196, 72, "s3", "S3", "comprobantes", ["privado · AES-256"])
flecha([(686, 188), (730, 188)])
flecha([(686, 290), (730, 290)])
flecha([(686, 397), (730, 397)])
flecha([(686, 486), (730, 486)])

# API Validaciones (nuevo)
box(486, 610, 220, 150, "lambda", "λ", "Validaciones (API)", ["GET /validaciones/{id}", "GET …/{id}/admin", "GET /validaciones/admin", "POST …/{id}/decision", "acciones internas del flujo"], nuevo=True)
box(730, 610, 210, 110, "ddb", "DB", "nexo-validaciones", ["PK id_operacion", "SK fecha_inicio", "GSI numero-operacion", "GSI estado-fecha"], nuevo=True)
flecha([(706, 665), (730, 665)])

# Usuarios -> borde -> API
flecha([(174, 190), (225, 170)], label="1 HTTPS", lx=196, ly=168)
flecha([(174, 215), (200, 215), (200, 380), (225, 380)], label="2 JSON + JWT", lx=200, ly=300)
flecha([(174, 500), (205, 500), (205, 440), (225, 440)], label="x-admin-key", lx=214, ly=482, lsize=10)
for y in (188, 296, 440):
    flecha([(440, 400), (462, 400), (462, y), (486, y)])
flecha([(440, 455), (455, 455), (455, 685), (486, 685)], color=NUEVO, label="rutas /validaciones", lx=395, ly=600)

# ---------------------------------------------------------------- Step Functions
SX, SY, SW, SH = 975, 110, 560, 790
a(f'<rect x="{SX}" y="{SY}" width="{SW}" height="{SH}" rx="12" fill="#FFF3F7" stroke="{NUEVO}" stroke-width="2.6"/>')
a(f'<rect x="{SX + 12}" y="{SY + 12}" width="38" height="38" rx="8" fill="{COL["sfn"]}"/>')
text(SX + 31, SY + 37, "SF", 15, True, "#fff", "middle")
text(SX + 60, SY + 30, "AWS Step Functions (Standard) — nexoguard", 15, True)
text(SX + 60, SY + 47, "Workflow agéntico: ruta predefinida + agentes Groq + revisión humana", 11.5, fill="#4A5568")
a(f'<rect x="{SX + SW - 54}" y="{SY - 9}" width="50" height="18" rx="9" fill="{NUEVO}"/>')
text(SX + SW - 29, SY + 4, "NUEVO", 10, True, "#fff", "middle")

cx = SX + 150     # columna central
pw = 260
steps = [("RegistrarInicio", "API Validaciones · estado en_curso", "lambda", "λ"),
         ("ExtraerComprobante", "Agente Extractor · Groq visión (lee S3)", "lambda", "λ"),
         ("VerificarCoincidencia", "Reglas: monto, cuenta, fecha, duplicado", "lambda", "λ"),
         ("EvaluarRiesgo", "Agente de Riesgo · Groq · semáforo + barreras", "lambda", "λ")]
y0 = SY + 70
for i, (t, s, k, g) in enumerate(steps):
    paso(cx, y0 + i * 70, pw, 48, t, s, k, g)
    if i:
        flecha([(cx + pw / 2, y0 + i * 70 - 22), (cx + pw / 2, y0 + i * 70)], COL["sfn"])
# Choice
dy = y0 + 4 * 70 + 10
dcx = cx + pw / 2
a(f'<polygon points="{dcx},{dy} {dcx + 80},{dy + 32} {dcx},{dy + 64} {dcx - 80},{dy + 32}" fill="#fff" stroke="{COL["sfn"]}" stroke-width="1.8"/>')
text(dcx, dy + 30, "DecidirRuta", 12, True, anchor="middle")
text(dcx, dy + 45, "(Choice)", 10.5, fill="#4A5568", anchor="middle")
flecha([(dcx, y0 + 3 * 70 + 48), (dcx, dy)], COL["sfn"])
by = dy + 100
ramas = [(SX + 18, "🟢 AprobarAutomatico", "→ En proceso", "#12A150"),
         (SX + 200, "🟡 NotificarRevision", "SNS → EsperarRevision (token)", "#C48A00"),
         (SX + 382, "🔴 RechazarAutomatico", "→ Rechazada con motivo", "#C62828")]
for x, t, s, c in ramas:
    a(f'<rect x="{x}" y="{by}" width="160" height="52" rx="8" fill="#fff" stroke="{c}" stroke-width="2"/>')
    text(x + 80, by + 21, t, 11.5, True, anchor="middle")
    text(x + 80, by + 38, s, 10.5, fill="#4A5568", anchor="middle")
flecha([(dcx - 80, dy + 32), (SX + 98, dy + 32), (SX + 98, by)], "#12A150")
flecha([(dcx, dy + 64), (dcx, by)], "#C48A00")
flecha([(dcx + 80, dy + 32), (SX + 462, dy + 32), (SX + 462, by)], "#C62828")
ay = by + 100
paso(cx, ay, pw, 48, "AplicarDecision", "Operaciones (invoke) · historial + actor", "lambda", "λ")
for x in (SX + 98, SX + 280, SX + 462):
    flecha([(x, by + 52), (x, ay - 14), (dcx, ay - 14), (dcx, ay)], COL["sfn"], w=1.4)
paso(cx, ay + 70, pw, 48, "GuardarValidacion", "API Validaciones · registro auditable", "lambda", "λ")
flecha([(dcx, ay + 48), (dcx, ay + 70)], COL["sfn"])
paso(cx, ay + 140, pw, 48, "AlertaCumplimiento", "Choice: 🔴 o monto ≥ umbral → SNS", "sns", "✉")
flecha([(dcx, ay + 118), (dcx, ay + 140)], COL["sfn"])
text(SX + SW / 2, SY + SH - 16, "Retry/Catch por estado · si Groq falla, la operación va a revisión humana (nunca se pierde)",
     11, True, COL["sfn"], "middle")

# ---------------------------------------------------------------- servicios a la derecha
box(1590, 230, 190, 100, "ext", "AI", "API Groq", ["qwen3.8-27b (visión)", "gpt-oss-20b (texto)", "sin memoria · HTTPS"], dash=True)
box(1590, 560, 190, 90, "sns", "SNS", "SNS nexoguard", ["correo a back-office", "y cumplimiento"], nuevo=True)
box(1590, 760, 190, 100, "cw", "CW", "CloudWatch", ["logs de Lambdas y", "ejecuciones · alarmas", "+ SNS alertas"])

# conexiones del workflow
flecha([(686, 441), (952, 441), (952, y0 + 24), (cx, y0 + 24)], NUEVO, label="3 StartExecution", lx=830, ly=436, lsize=10.5)
flecha([(cx, y0 + 70 + 24), (945, y0 + 94), (945, 500), (926, 500)], COL["s3"], label="lee comprobante", lx=1060, ly=y0 + 88, dash=True, lsize=10.5)
flecha([(cx + pw, y0 + 70 + 24), (1590, 260)], COL["ext"], label="4 visión", lx=1490, ly=225)
flecha([(cx + pw, y0 + 210 + 24), (1590, 300)], COL["ext"], label="5 riesgo", lx=1510, ly=330)
flecha([(cx, ay + 24), (959, ay + 24), (959, 540), (600, 540), (600, 522)], COL["sfn"], label="aplicar_decision", lx=760, ly=535, dash=True, lsize=10.5)
flecha([(cx, ay + 94), (966, ay + 94), (966, 785), (640, 785), (640, 760)], COL["sfn"], label="iniciar · registrar_espera · guardar", lx=820, ly=780, dash=True, lsize=10.5)
flecha([(SX + 280, by + 52), (SX + 280, by + 60), (1560, by + 60), (1560, 590), (1590, 590)], COL["sns"], dash=True)
flecha([(cx + pw, ay + 164), (1560, ay + 164), (1560, 630), (1590, 630)], COL["sns"], label="alerta", lx=1500, ly=ay + 158)
flecha([(1590, 640), (1575, 640), (1575, 928), (190, 928), (190, 842), (174, 842)], COL["sns"], label="6 correo", lx=1300, ly=922, dash=True)
flecha([(190, 842), (190, 580), (174, 580)], COL["sns"], dash=True)
# decisión humana
flecha([(174, 520), (186, 520), (186, 760), (486, 760)], NUEVO, label="7 Aprobar / Rechazar", lx=330, ly=778)
flecha([(596, 610), (596, 590), (970, 590), (970, by + 66), (SX + 240, by + 66), (SX + 240, by + 52)], NUEVO, label="SendTaskSuccess", lx=780, ly=584, lsize=10.5)

# leyenda / decisiones
a('<rect x="225" y="800" width="720" height="104" rx="10" fill="#F4F7FF" stroke="#8FA6E8"/>')
notas = ["• La IA extrae datos y explica; las reglas deterministas deciden. El agente puede escalar a revisión, nunca aprobar lo que las reglas no aprueban.",
         "• Cada microservicio mantiene su propia BD: el workflow cambia operaciones solo vía Operaciones y guarda el análisis solo vía Validaciones.",
         "• Groq reemplaza a Amazon Bedrock (no disponible en AWS Academy). El nombre del modelo es un parámetro del template.",
         "• Duplicados: GSI numero-operacion en nexo-validaciones. Clave Groq como parámetro NoEcho (en producción: Secrets Manager)."]
for i, n in enumerate(notas):
    text(237, 824 + i * 21, n, 11.5)
text(W / 2, 950, "Flujo NexoGuard: cliente adjunta comprobante → StartExecution → extraer (IA) → verificar (reglas) → riesgo (IA + barreras) →",
     13, True, "#0E1B33", "middle")
text(W / 2, 972, "aprobar automático | revisión humana (waitForTaskToken) | rechazar → aplicar decisión → registro auditable → alertas por correo",
     13, True, "#0E1B33", "middle")
a('</svg>')

svg = DIR / "arquitectura_nexoguard.svg"
svg.write_text("\n".join(out), encoding="utf-8")
navegador = next((p for p in [shutil.which("chrome"), shutil.which("msedge"),
                              "C:/Program Files/Google/Chrome/Application/chrome.exe",
                              "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"] if p and Path(p).exists()), None)
if navegador:
    png = DIR / "arquitectura_nexoguard.png"
    subprocess.run([navegador, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={W},{H}",
                    "--force-device-scale-factor=2", f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
    print("ok:", svg.name, png.name)
else:
    print("ok:", svg.name, "(sin navegador para el PNG)")

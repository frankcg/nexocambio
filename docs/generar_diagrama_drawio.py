#!/usr/bin/env python3
"""Genera docs/arquitectura_nexocambio.drawio (XML de draw.io / diagrams.net).

Mismo contenido y layout que docs/generar_diagrama.py (version SVG/PNG), pero como archivo
editable en draw.io (app.diagrams.net o la extension de VS Code). No usa iconos oficiales de
AWS (para no depender de nombres exactos de la libreria mxgraph.aws4): cada servicio es un
rectangulo con una insignia de color + sigla, igual que en el diagrama SVG. Si se quiere el
look oficial, en draw.io: Mas formas > AWS / AWS19, y arrastrar el icono real sobre cada caja.
"""
from xml.sax.saxutils import escape as _esc

W, H = 1600, 980
COL = {"lambda": "#ED7100", "api": "#8C4FFF", "ddb": "#3B48CC", "s3": "#3F8624",
       "cw": "#E7157B", "ext": "#5B6B85", "user": "#232F3E"}

cells = []
_n = [0]


def nid(prefix="c"):
    _n[0] += 1
    return f"{prefix}{_n[0]}"


def esc(s):
    return _esc(s, {'"': "&quot;"})


def vertex(id_, value, style, x, y, w, h, parent="1"):
    cells.append(f'<mxCell id="{id_}" value="{esc(value)}" style="{style}" vertex="1" parent="{parent}">'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


SIDE = {"right": (1, 0.5), "left": (0, 0.5), "top": (0.5, 0), "bottom": (0.5, 1)}


def conn(src, src_side, tgt, tgt_side, label="", color="#232F3E", dashed=False, fs=11, w=2):
    ex, ey = SIDE[src_side]
    en, eny = SIDE[tgt_side]
    style = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;endSize=7;"
              f"exitX={ex};exitY={ey};exitDx=0;exitDy=0;entryX={en};entryY={eny};entryDx=0;entryDy=0;"
              f"strokeColor={color};strokeWidth={w};fontColor={color};fontSize={fs};jettySize=auto;"
              + ("dashed=1;dashPattern=6 5;" if dashed else ""))
    eid = nid("e")
    cells.append(f'<mxCell id="{eid}" value="{esc(label)}" style="{style}" edge="1" parent="1" '
                 f'source="{src}" target="{tgt}"><mxGeometry relative="1" as="geometry"/></mxCell>')
    return eid


def box(x, y, w, h, kind, glyph, titulo, lineas=(), dash=False, tsize=14, id_=None):
    c = COL[kind]
    bid = id_ or nid("box")
    style = ("rounded=1;arcSize=8;whiteSpace=wrap;html=1;fillColor=#FFFFFF;"
             f"strokeColor={c};strokeWidth=2;" + ("dashed=1;dashPattern=6 5;" if dash else ""))
    vertex(bid, "", style, x, y, w, h)
    vertex(f"{bid}_ic", glyph,
           f"rounded=1;arcSize=25;whiteSpace=wrap;html=1;fillColor={c};strokeColor=none;"
           "fontColor=#FFFFFF;fontStyle=1;fontSize=15;align=center;verticalAlign=middle;",
           10, 10, 42, 42, parent=bid)
    vertex(f"{bid}_ti", titulo,
           f"text;html=1;align=left;verticalAlign=top;fontStyle=1;fontSize={tsize};fontColor=#232F3E;"
           "whiteSpace=wrap;", 62, 8, w - 72, 26, parent=bid)
    if lineas:
        val = "<br>".join(esc(l) for l in lineas)
        vertex(f"{bid}_de", val,
               "text;html=1;align=left;verticalAlign=top;fontSize=11.5;fontColor=#4A5568;"
               "whiteSpace=wrap;lineHeight=130%;", 62, 8 + tsize + 10, w - 72,
               h - (8 + tsize + 10) - 6, parent=bid)
    return bid


def nota(x, y, w, h, color, titulo, cuerpo, dash=False, fill="#FFFFFF", title_color=None,
         tsize=13, id_=None, title_h=34):
    bid = id_ or nid("nota")
    style = (f"rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={color};"
             "strokeWidth=1.2;" + ("dashed=1;dashPattern=4 3;" if dash else ""))
    vertex(bid, "", style, x, y, w, h)
    tc = title_color or color
    body_y = 10 + title_h
    vertex(f"{bid}_ti", titulo,
           f"text;html=1;align=left;verticalAlign=top;fontStyle=1;fontSize={tsize};fontColor={tc};"
           "whiteSpace=wrap;", 14, 10, w - 24, title_h, parent=bid)
    vertex(f"{bid}_de", cuerpo,
           "text;html=1;align=left;verticalAlign=top;fontSize=12;fontColor=#232F3E;whiteSpace=wrap;"
           "lineHeight=138%;", 14, body_y, w - 24, h - body_y - 8, parent=bid)
    return bid


def actor(id_, x, y, w, h, emoji, titulo, subtitulo):
    style = ("rounded=1;arcSize=14;whiteSpace=wrap;html=1;fillColor=#FFFFFF;"
              f"strokeColor={COL['user']};strokeWidth=2;")
    vertex(id_, "", style, x, y, w, h)
    vertex(f"{id_}_ic", emoji,
           "text;html=1;align=center;verticalAlign=middle;fontSize=30;", 0, 8, w, 42, parent=id_)
    vertex(f"{id_}_ti", titulo,
           "text;html=1;align=center;verticalAlign=top;fontStyle=1;fontSize=13;fontColor=#232F3E;",
           0, 52, w, 20, parent=id_)
    vertex(f"{id_}_su", subtitulo,
           "text;html=1;align=center;verticalAlign=top;fontSize=11;fontColor=#4A5568;whiteSpace=wrap;",
           4, 72, w - 8, h - 76, parent=id_)


def texto(x, y, w, h, value, size=13, bold=False, color="#232F3E", align="left", italic=False):
    style = (f"text;html=1;align={align};verticalAlign=middle;fontSize={size};fontColor={color};"
             "whiteSpace=wrap;" + ("fontStyle=5;" if bold and italic else
                                    ("fontStyle=1;" if bold else ("fontStyle=2;" if italic else ""))))
    vertex(nid("t"), value, style, x, y, w, h)


# ------------------------------------------------------------------ título
texto(0, 6, W, 46, "Arquitectura AWS del MVP — NexoCambio", 26, bold=True, color="#0E1B33", align="center")
texto(0, 54, W, 24,
      "Microservicios serverless · AWS Academy Learner Lab · Región us-east-1 (N. Virginia) · "
      "Stack en CloudFormation", 13, color="#4A5568", align="center")

# ------------------------------------------------------------------ región AWS Cloud
vertex("region", "AWS Cloud — us-east-1",
       "rounded=1;arcSize=3;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#232F3E;"
       "strokeWidth=1.5;verticalAlign=top;align=left;spacingLeft=16;spacingTop=8;fontStyle=1;"
       "fontSize=13;", 190, 98, 1385, 820)

# ------------------------------------------------------------------ actores
actor("cliente", 20, 395, 140, 130, "🧑", "Cliente web", "desktop · móvil")
actor("backoffice", 20, 580, 140, 105, "🔑", "Back-office", "/admin · x-admin-key")

# ------------------------------------------------------------------ frontend + API
box(225, 150, 230, 118, "s3", "S3", "S3 — Sitio web",
    ["Frontend Angular (SPA)", "Cotizador · operar · login · registro · mis operaciones",
     "Back-office en /#/admin", "Servido por HTTPS"], tsize=14, id_="s3web")
box(225, 278, 230, 96, "api", "CF", "CloudFront (opt-in)",
    ["Delante de S3 — Sitio web", "UsarHttps=true · dominio *.cloudfront.net",
     "Deniega en Learner Lab (rol voclabs)"], dash=True, tsize=13.5, id_="cloudfront")
box(225, 385, 230, 130, "api", "API", "API Gateway",
    ["HTTP API · stage v1", "CORS · throttling", "11 rutas → 3 Lambdas"], tsize=14, id_="apigw")

conn("cloudfront", "top", "s3web", "bottom", color="#5B6B85", dashed=True)
conn("cliente", "right", "s3web", "left", "① HTTPS (Angular)")
conn("cliente", "right", "apigw", "left", "② HTTPS + JSON + JWT")
conn("backoffice", "right", "apigw", "left", "④ HTTPS + JSON + x-admin-key")

# ------------------------------------------------------------------ cómputo (Lambda)
vertex("compute", "Cómputo — AWS Lambda (Python 3.12)",
       "rounded=1;arcSize=4;whiteSpace=wrap;html=1;fillColor=#FFF6EC;strokeColor=#ED7100;"
       "strokeWidth=1.5;dashed=1;dashPattern=7 5;verticalAlign=top;align=left;spacingLeft=14;"
       "spacingTop=6;fontStyle=1;fontSize=12.5;fontColor=#B45309;", 560, 132, 290, 700)

box(585, 175, 240, 118, "lambda", "λ", "Cotizaciones",
    ["POST /cotizar", "Tasa, monto, vigencia 5 min", "Tasas en vivo con caché"], id_="lambda_cot")
box(585, 385, 240, 130, "lambda", "λ", "Operaciones",
    ["POST/GET /operaciones", "POST …/comprobante", "Back-office (x-admin-key):",
     "GET …/admin, …/{id}/admin", "PATCH …/{id}/estado"], id_="lambda_ops")
box(585, 600, 240, 118, "lambda", "λ", "Clientes / Auth",
    ["POST /registro · POST /login", "GET /clientes/{id}", "PBKDF2 + JWT HS256"], id_="lambda_cli")

nota(585, 740, 240, 80, "#ED7100", "Lambda Layer: nexo_common",
     "JWT · hash · validaciones · respuestas<br>Rol de ejecución: LabRole (Learner Lab)",
     dash=True, title_color="#B45309", tsize=12, id_="layer", title_h=20)

conn("apigw", "right", "lambda_cot", "left")
conn("apigw", "right", "lambda_ops", "left")
conn("apigw", "right", "lambda_cli", "left")
# círculo con el número 3 (orden del flujo), encima de las flechas de enrutamiento
vertex("n3bg", "", "ellipse;whiteSpace=wrap;html=1;fillColor=#232F3E;strokeColor=none;", 505, 330, 22, 22)
vertex("n3tx", "3", "text;html=1;align=center;verticalAlign=middle;fontSize=12;fontStyle=1;"
       "fontColor=#FFFFFF;", 505, 330, 22, 22)
conn("lambda_ops", "top", "lambda_cot", "bottom", "Lambda Invoke:<br>obtener cotización",
     color="#B45309", w=2.2)

# ------------------------------------------------------------------ datos
box(985, 150, 250, 60, "ddb", "DB", "nexo-tasas", ["PK moneda"], tsize=13.5, id_="ddb_tasas")
box(985, 222, 250, 76, "ddb", "DB", "nexo-cotizaciones",
    ["PK id_cotizacion", "TTL: se auto-elimina"], tsize=13.5, id_="ddb_cotiz")
box(985, 372, 250, 92, "ddb", "DB", "nexo-operaciones",
    ["PK id_operacion", "GSI cliente-fecha-index", "Scan (listado back-office)"], tsize=13.5,
    id_="ddb_oper")
box(985, 476, 250, 76, "s3", "S3", "S3 comprobantes",
    ["Privado · cifrado AES-256", "URL temporal firmada"], tsize=13.5, id_="s3_comp")
box(985, 615, 250, 90, "ddb", "DB", "nexo-clientes",
    ["pk = CLI# · EMAIL# · DOC#", "Unicidad por transacción"], tsize=13.5, id_="ddb_cli")

conn("lambda_cot", "right", "ddb_tasas", "left")
conn("lambda_cot", "right", "ddb_cotiz", "left")
conn("lambda_ops", "right", "ddb_oper", "left")
conn("lambda_ops", "right", "s3_comp", "left")
conn("lambda_cli", "right", "ddb_cli", "left")

texto(1290, 118, 275, 20, "BD del microservicio Cotizaciones", 11, color="#3B48CC", align="center", italic=True)
texto(1290, 340, 275, 20, "BD y archivos del microservicio Operaciones", 11, color="#3B48CC", align="center", italic=True)
texto(1290, 583, 275, 20, "BD del microservicio Clientes", 11, color="#3B48CC", align="center", italic=True)

# ------------------------------------------------------------------ fuente externa
box(1290, 150, 265, 118, "ext", "↗", "APIs públicas de tasas",
    ["FX (PEN/EUR) y cripto (BTC, ETH, USDT, USDC)", "Vía internet · 1 consulta/5 min"],
    dash=True, id_="ext_api")
conn("lambda_cot", "top", "ext_api", "left", "HTTPS (opcional; con caché en DynamoDB)",
     color="#5B6B85", dashed=True, fs=10.5)

# ------------------------------------------------------------------ monitoreo
box(985, 760, 250, 100, "cw", "CW", "CloudWatch",
    ["Logs (14 días) · métricas", "Alarmas: errores Lambda y 5xx de la API"], tsize=13.5, id_="cw")
box(1290, 760, 265, 100, "cw", "SNS", "SNS — alertas",
    ["Notificación por correo cuando salta una alarma"], tsize=13.5, id_="sns")

conn("layer", "right", "cw", "left", color="#E7157B", dashed=True)
conn("cw", "right", "sns", "left", color="#E7157B", dashed=True)
conn("apigw", "bottom", "cw", "bottom", "métricas de la API", color="#E7157B", dashed=True)

# ------------------------------------------------------------------ notas
notas_html = "<br>".join([
    "• Cada microservicio tiene su propia base de datos.",
    "• Operaciones NO confía en la tasa del navegador: la valida con Cotizaciones (Lambda→Lambda).",
    "• Contraseñas con PBKDF2; sesión con JWT (2 h).",
    "• Back-office (/admin): clave compartida x-admin-key en vez de JWT; aprueba o rechaza.",
    "• Comprobantes: bucket privado, validación de formato real y enlaces temporales.",
    "• Pago por uso: sin servidores encendidos 24×7.",
    "• Frontend Angular en S3, por HTTPS (endpoint REST de S3).",
    "• Todo el stack (Lambdas, DynamoDB, S3, API, CloudFront) se aprovisiona con CloudFormation (deploy.sh).",
])
nota(1290, 300, 265, 440, "#3B48CC", "Decisiones de diseño", notas_html, fill="#F0F5FF",
     tsize=13.5, id_="notas")

fuera_html = "Cognito (usuarios y roles reales)<br><br>EventBridge + SES (avisos de estado)"
nota(20, 705, 150, 150, "#8A94A6", "Fuera de alcance (no implementado):", fuera_html,
     dash=True, title_color="#5B6B85", tsize=11.5, id_="fuera")

# ------------------------------------------------------------------ pie
texto(0, 942, W, 30,
      "Flujo MVP: cotizar → registrarse / iniciar sesión → registrar operación → adjuntar "
      "comprobante → back-office aprueba o rechaza → consultar estado", 13, bold=True,
      color="#0E1B33", align="center")

xml = f'''<mxfile host="app.diagrams.net" agent="generar_diagrama_drawio.py" version="24.7.17" type="device">
  <diagram name="Arquitectura NexoCambio" id="nexocambio-arquitectura">
    <mxGraphModel dx="1600" dy="980" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{W}" pageHeight="{H}" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        {"".join(cells)}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
'''

open("docs/arquitectura_nexocambio.drawio", "w", encoding="utf-8").write(xml)
print("ok", len(cells), "celdas")

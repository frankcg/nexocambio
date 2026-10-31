"""Genera comprobantes de transferencia FICTICIOS para probar NexoGuard.

Cada imagen lleva la marca de agua "DOCUMENTO FICTICIO" y no usa logos de bancos.
Las cuentas de destino son las cuentas demo de NexoCambio (frontend/.../cuentas-nexo.ts).

Uso: python scripts/generar_comprobantes.py [AAAA-MM-DD] [--semilla N]  ->  tests/fixtures/comprobantes/*.png
La fecha por defecto es HOY: regenerarlos el día de la demo (NexoGuard revisa que el comprobante
no sea anterior a la operación). La semilla cambia los números de operación, para que una nueva
corrida no choque con la detección de duplicados (la usa postman/generar_nexoguard.py).
"""
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SALIDA = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "comprobantes"
FUENTES = Path("C:/Windows/Fonts")
W, H = 420, 760

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
         "Octubre", "Noviembre", "Diciembre"]
DIA = date.today()
SEMILLA = 0


def nro(base):
    """Número de operación desplazado por la semilla (mismo largo que el original)."""
    return f"{(int(base) + SEMILLA) % 10 ** len(base):0{len(base)}d}"


def fecha(hora):
    return f"{DIAS[DIA.weekday()]} {DIA.day} {MESES[DIA.month - 1]} {DIA.year} - {hora}"


COLORES = {"BCP": "#0A4FA6", "Interbank": "#05A660", "BBVA": "#072146", "Scotiabank": "#C8102E"}


def fuente(tam, negrita=False):
    try:
        return ImageFont.truetype(str(FUENTES / ("arialbd.ttf" if negrita else "arial.ttf")), tam)
    except OSError:
        return ImageFont.load_default(tam)


def marca_agua(img):
    capa = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for y in range(0, H * 2, 170):
        d.text((40, y), "DOCUMENTO FICTICIO · SOLO PRUEBAS", font=fuente(30, True), fill=(200, 30, 30, 45))
    capa = capa.rotate(32, center=(W, H)).crop((W // 2, H // 2, W // 2 + W, H // 2 + H))
    return Image.alpha_composite(img, capa)


def comprobante(c):
    img = Image.new("RGBA", (W, H), "white")
    d = ImageDraw.Draw(img)
    color = COLORES[c["banco"]]
    d.rectangle((0, 0, W, 70), fill=color)
    d.text((24, 22), c["banco"].upper(), font=fuente(26, True), fill="white")
    d.text((W - 24, 30), "Constancia", font=fuente(15), fill="white", anchor="ra")

    d.text((W / 2, 105), c["tipo"], font=fuente(17), fill="#333", anchor="mm")
    d.text((W / 2, 150), c["monto"], font=fuente(40, True), fill=color, anchor="mm")
    d.text((W / 2, 190), c["fecha"], font=fuente(14), fill="#777", anchor="mm")
    d.text((W / 2, 235), "Detalle del movimiento", font=fuente(15, True), fill="#222", anchor="mm")

    y = 270
    for etiqueta, valores in c["filas"]:
        d.text((24, y), etiqueta, font=fuente(15), fill="#444")
        for i, v in enumerate(valores):
            d.text((W - 24, y + i * 22), v, font=fuente(15, i == 0), fill="#222" if i == 0 else "#777", anchor="ra")
        y += max(1, len(valores)) * 22 + 22
        d.line((24, y - 12, W - 24, y - 12), fill="#E3E3E3")

    if c.get("mensaje"):
        d.rounded_rectangle((24, y, W - 24, y + 70), radius=8, outline="#DDD")
        d.text((36, y + 10), "Mensaje", font=fuente(14, True), fill="#222")
        d.text((36, y + 34), c["mensaje"], font=fuente(14), fill="#444")

    d.text((W / 2, H - 22), "Documento ficticio generado para pruebas académicas", font=fuente(11), fill="#999", anchor="mm")
    img = marca_agua(img).convert("RGB")
    if c.get("borroso"):
        img = img.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(1.2)).resize((W, H))
    return img


def filas(destino, cuenta, banco_dest, total, origen, cuenta_origen, n_op):
    return [
        ("Enviado a", [destino, cuenta, banco_dest]),
        ("Comisión", ["S/ 0.00"]),
        ("Total cobrado", [total]),
        ("Desde", [origen, cuenta_origen]),
        ("Número de operación", [n_op]),
    ]


# Escenarios: el nombre indica el resultado esperado del workflow.
def casos():  # se evalúa al generar: usa DIA y SEMILLA
    return {
    # Verde: S/ 1,000.00 a la cuenta BCP soles de NexoCambio (mismo monto que el ejemplo del cotizador).
    "01_ok_bcp_pen_1000": dict(
        banco="BCP", tipo="TRANSFERENCIA A TERCEROS", monto="S/ 1,000.00", fecha=fecha("10:15 am"),
        filas=filas("NexoCambio S.A.C.", "**** 0-39", "BCP - Soles", "S/ 1,000.00", "Cuenta Digital Soles", "****4821", nro("04417382")),
        mensaje="Operación de cambio NexoCambio"),
    # Verde: interbancaria Interbank -> BCP de NexoCambio, S/ 250.00.
    "02_ok_interbank_pen_250": dict(
        banco="Interbank", tipo="TRANS. INTERBANCARIA", monto="S/ 250.00", fecha=fecha("11:42 am"),
        filas=filas("NexoCambio S.A.C.", "CCI ****0039-14", "BCP - Soles", "S/ 250.00", "Cuenta Simple Soles", "****9177", nro("000552318")),
        mensaje="Cambio de soles a dólares"),
    # Rojo: el monto (S/ 850.00) no coincide con una operación de S/ 1,000.00.
    "03_rojo_monto_distinto": dict(
        banco="BCP", tipo="TRANSFERENCIA A TERCEROS", monto="S/ 850.00", fecha=fecha("12:03 pm"),
        filas=filas("NexoCambio S.A.C.", "**** 0-39", "BCP - Soles", "S/ 850.00", "Cuenta Digital Soles", "****4821", nro("04419056"))),
    # Rojo: transferido a una cuenta que no es de NexoCambio.
    "04_rojo_cuenta_ajena": dict(
        banco="BBVA", tipo="TRANSFERENCIA A OTROS BANCOS", monto="S/ 1,000.00", fecha=fecha("12:30 pm"),
        filas=filas("Inversiones Andinas E.I.R.L.", "**** 7716", "Scotiabank - Soles", "S/ 1,000.00", "Cuenta Ganadora", "****3305", nro("7781200345"))),
    # Rojo: reutiliza el N° de operación 04417382 del caso 01 (comprobante duplicado).
    "05_rojo_duplicado_de_01": dict(
        banco="BCP", tipo="TRANSFERENCIA A TERCEROS", monto="S/ 1,000.00", fecha=fecha("10:15 am"),
        filas=filas("NexoCambio S.A.C.", "**** 0-39", "BCP - Soles", "S/ 1,000.00", "Cuenta Digital Soles", "****4821", nro("04417382")),
        mensaje="Operación de cambio NexoCambio"),
    # Amarillo: monto alto (US$ 12,000.00), supera el umbral de registro UIF.
    "06_amarillo_monto_alto_usd": dict(
        banco="Scotiabank", tipo="TRANSFERENCIA INTERBANCARIA", monto="US$ 12,000.00", fecha=fecha("03:20 pm"),
        filas=[("Enviado a", ["NexoCambio S.A.C.", "CCI ****1147-17", "BCP - Dólares"]), ("Comisión", ["US$ 0.00"]),
               ("Total cobrado", ["US$ 12,000.00"]), ("Desde", ["Cuenta Empresa Dólares", "****6620"]),
               ("Número de operación", [nro("90034417")])],
        mensaje="Importaciones del Sur S.A.C. - cambio"),
    # Amarillo: imagen borrosa / ilegible.
    "07_amarillo_borroso": dict(
        banco="Interbank", tipo="TRANS. INTERBANCARIA", monto="S/ 500.00", fecha=fecha("04:05 pm"),
        filas=filas("NexoCambio S.A.C.", "CCI ****0039-14", "BCP - Soles", "S/ 500.00", "Cuenta Simple Soles", "****2290", nro("000561904")),
        borroso=True),
}


def no_comprobante():
    """Amarillo: una imagen que no es un comprobante bancario (ticket de consumo)."""
    img = Image.new("RGBA", (W, H), "#FFFDF5")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 60), "CAFETERÍA LA ESQUINA", font=fuente(22, True), fill="#333", anchor="mm")
    d.text((W / 2, 90), "Ticket de venta N° 001-2231", font=fuente(14), fill="#666", anchor="mm")
    y = 150
    for item, precio in [("Café americano", "S/ 8.50"), ("Sándwich mixto", "S/ 12.00"), ("Jugo de naranja", "S/ 9.00")]:
        d.text((40, y), item, font=fuente(16), fill="#333")
        d.text((W - 40, y), precio, font=fuente(16), fill="#333", anchor="ra")
        y += 34
    d.line((40, y, W - 40, y), fill="#999")
    d.text((40, y + 16), "TOTAL", font=fuente(18, True), fill="#111")
    d.text((W - 40, y + 16), "S/ 29.50", font=fuente(18, True), fill="#111", anchor="ra")
    d.text((W / 2, H - 22), "Documento ficticio generado para pruebas académicas", font=fuente(11), fill="#999", anchor="mm")
    return marca_agua(img).convert("RGB")


def generar(salida=SALIDA, dia=None, semilla=0):
    global DIA, SEMILLA
    DIA, SEMILLA = dia or date.today(), semilla
    salida.mkdir(parents=True, exist_ok=True)
    for nombre, caso in casos().items():
        comprobante(caso).save(salida / f"{nombre}.png")
    no_comprobante().save(salida / "08_amarillo_no_es_comprobante.png")
    return salida


def main():
    args = sys.argv[1:]
    semilla = int(args[args.index("--semilla") + 1]) if "--semilla" in args else 0
    fechas = [a for a in args if "-" in a and a[:4].isdigit()]
    generar(SALIDA, date.fromisoformat(fechas[0]) if fechas else None, semilla)
    print(f"8 comprobantes en {SALIDA}")


if __name__ == "__main__":
    main()

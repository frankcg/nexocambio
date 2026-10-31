#!/usr/bin/env python3
"""Carga datos de demostración: reinicia el entorno y deja operaciones verdes, rojas y amarillas.

Uso:  python scripts/cargar_demo.py <ApiUrl> [--sin-reiniciar]

1. POST /demo/reiniciar (incluir_operaciones): detiene ejecuciones, vacía validaciones y operaciones,
   reinicia el banco simulado con sus datos semilla.
2. Genera comprobantes nuevos y registra sus depósitos en el banco simulado.
3. Con el cliente demo (demo@nexocambio.pe / Demo1234) crea:
     🟢 2 aprobadas automáticamente     🔴 2 rechazadas automáticamente
     🟡 4 en revisión (quedan pendientes en el back-office para la demo)
Tarda ~5 min: la capa gratuita de Groq admite ~3 imágenes por minuto y la conciliación espera al banco.
"""
import random
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generar_comprobantes as gc  # noqa: E402
import probar_nexoguard as pn  # noqa: E402

CORREO, PASSWORD = "demo@nexocambio.pe", "Demo1234"


def main():
    if "--sin-reiniciar" not in sys.argv:
        s, r = pn.llamar("POST", "/demo/reiniciar", {"incluir_operaciones": True}, admin=True)
        print("Reinicio:", s, {k: v for k, v in r.items() if k != "mensaje"})
    token = pn.sesion(CORREO, PASSWORD, dni="70707070")
    interbank = {"tipo": "banco", "banco": "Interbank"}
    plan = [  # (color, descripción, comprobante, cotización, origen, destino, número declarado)
        ("verde", "S/ 1,000 · depósito confirmado", "01", pn.PEN, pn.BCP, pn.DEST_USD, None),
        ("verde", "S/ 250 · interbancaria confirmada", "02", {**pn.PEN, "monto_origen": 250}, interbank, pn.DEST_USD, None),
        ("rojo", "transferido a una cuenta ajena", "04", pn.PEN, pn.BCP, pn.DEST_USD, None),
        ("rojo", "comprobante duplicado del 01", "05", pn.PEN, pn.BCP, pn.DEST_USD, None),
        ("amarillo", "US$ 12,000 · umbral UIF", "06", pn.USD, {"tipo": "banco", "banco": "Scotiabank"}, pn.DEST_PEN, None),
        ("amarillo", "monto distinto (S/ 850)", "03", pn.PEN, pn.BCP, pn.DEST_USD, None),
        ("amarillo", "comprobante sin depósito en el banco", "09", pn.PEN, pn.BCP, pn.DEST_USD, None),
        ("amarillo", "imagen borrosa", "07", {**pn.PEN, "monto_origen": 500}, interbank, pn.DEST_USD, None),
    ]
    creadas = []
    with tempfile.TemporaryDirectory() as tmp:
        img = {p.stem[:2]: p for p in gc.generar(Path(tmp), semilla=random.randint(1, 9_000_000)).glob("*.png")}
        print("Depósitos registrados en el banco simulado:", len(gc.registrar_depositos(pn.API, pn.BANCO_KEY)))
        for color, desc, clave, cot, origen, destino, numero in plan:
            id_op = pn.operacion(token, cot, origen, destino, img[clave], numero)
            creadas.append((color, desc, id_op))
            print(f"  {color:8s} {id_op}  {desc}", flush=True)
            if clave == "01":                      # el duplicado (05) necesita que el 01 ya esté registrado
                pn.esperar(id_op, token, "finalizada")
            time.sleep(15)                         # respeta el límite por minuto de Groq
    print("\nEsperando el resultado de NexoGuard…")
    ok = True
    for color, desc, id_op in creadas:
        v, _ = pn.esperar(id_op, token, "en_revision" if color == "amarillo" else "finalizada")
        a = pn.analisis(id_op)
        obtenido = {"En proceso": "verde", "Rechazada": "rojo"}.get(v.get("estado_final"), "amarillo") \
            if v["estado"] == "finalizada" else "amarillo"
        ok &= obtenido == color
        print(f"  {'✓' if obtenido == color else '✗'} {color:8s} {id_op}  {desc} → {v['estado']}"
              f"{' · ' + v['estado_final'] if v.get('estado_final') else ''} · semáforo {a.get('semaforo')}")
    print(f"\nListo. Cliente demo: {CORREO} / {PASSWORD}. Las amarillas esperan decisión en el back-office.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

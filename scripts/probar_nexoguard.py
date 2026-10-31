#!/usr/bin/env python3
"""Prueba NexoGuard de punta a punta contra la API desplegada (los mismos escenarios que Postman, carpeta 6).

Uso:  python scripts/probar_nexoguard.py <ApiUrl> [--reiniciar]
Genera comprobantes con fecha de hoy y números nuevos, registra en el banco simulado los depósitos de los
comprobantes legítimos, crea un cliente de prueba y recorre los escenarios verde, rojo y amarillo.
--reiniciar: antes de empezar llama a POST /demo/reiniciar (vacía validaciones y reinicia el banco).
"""
import base64
import json
import random
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import generar_comprobantes as gc  # noqa: E402

API = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else ""
ADMIN = (RAIZ / ".secrets" / "admin_key").read_text().strip()
BANCO_KEY = (RAIZ / ".secrets" / "banco_key").read_text().strip()

PEN = {"modalidad": "casa", "moneda_origen": "PEN", "moneda_destino": "USD", "monto_origen": 1000}
USD = {"modalidad": "casa", "moneda_origen": "USD", "moneda_destino": "PEN", "monto_origen": 12000}
BCP = {"tipo": "banco", "banco": "BCP"}
DEST_USD = {"tipo": "banco", "banco": "Interbank", "tipo_cuenta": "Ahorros", "numero": "8983141592653", "titular": "Cliente Demo"}
DEST_PEN = {"tipo": "banco", "banco": "BCP", "tipo_cuenta": "Corriente", "numero": "19324587100391", "titular": "Cliente Demo"}


def llamar(metodo, ruta, cuerpo=None, token=None, admin=False):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if admin:
        h["x-admin-key"] = ADMIN
    req = urllib.request.Request(API + ruta, method=metodo, headers=h,
                                 data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def esperar(id_op, token, hasta, max_seg=300):
    t0 = time.time()
    while time.time() - t0 < max_seg:
        s, v = llamar("GET", f"/validaciones/{id_op}", token=token)
        if s == 200 and (v["estado"] == hasta or (hasta == "en_revision" and v["estado"] == "finalizada")):
            return v, time.time() - t0
        time.sleep(4)
    raise TimeoutError(f"{id_op} no llegó a {hasta}")


def operacion(token, cot, origen, destino, imagen, numero=None):
    s, q = llamar("POST", "/cotizar", cot)
    assert s == 201, q
    s, op = llamar("POST", "/operaciones", {"id_cotizacion": q["id_cotizacion"], "origen": origen, "destino": destino}, token)
    assert s == 201, op
    s, r = llamar("POST", f"/operaciones/{op['id_operacion']}/comprobante",
                  {"nombre_archivo": imagen.name, "content_type": "image/png",
                   "contenido_base64": base64.b64encode(imagen.read_bytes()).decode(),
                   **({"numero_transferencia": numero} if numero else {})}, token)
    assert s == 200 and r["estado"] == "Pendiente de validación", r
    return op["id_operacion"]


def sesion(correo, password="Clave1234", dni=None):
    """Registra al cliente (si ya existe, solo inicia sesión) y devuelve su token."""
    dni = dni or str(random.randint(10_000_000, 99_999_999))
    llamar("POST", "/registro", {"tipo_cliente": "persona", "nombres": "Cliente", "apellidos": "Demo NexoGuard",
                                 "tipo_documento": "DNI", "numero_documento": dni, "fecha_nacimiento": "1994-05-10",
                                 "telefono": "9" + dni, "ocupacion": "Dependiente", "pep": False,
                                 "correo": correo, "password": password})
    s, r = llamar("POST", "/login", {"correo": correo, "password": password})
    assert s == 200, r
    return r["token"]


def analisis(id_op):
    s, det = llamar("GET", f"/validaciones/{id_op}/admin", admin=True)
    return det["validaciones"][0] if s == 200 else {}


def main():
    if "--reiniciar" in sys.argv:
        print("Reinicio:", llamar("POST", "/demo/reiniciar", {}, admin=True)[1])
    token = sesion(f"nexoguard{random.randint(10_000_000, 99_999_999)}@correo.com")
    resultados = []

    def reportar(nombre, id_op, ok, detalle):
        resultados.append((nombre, id_op, ok, detalle))
        print(("OK    " if ok else "FALLA ") + nombre, "·", detalle, flush=True)

    with tempfile.TemporaryDirectory() as tmp:
        img = {p.stem[:2]: p for p in gc.generar(Path(tmp), semilla=random.randint(1, 9_000_000)).glob("*.png")}
        print("Depósitos en el banco simulado:", [(k, e) for k, _, e in gc.registrar_depositos(API, BANCO_KEY)])

        # Decisiones automáticas del agente
        for nombre, clave, cot, origen, esperado, numero in [
            ("Verde: aprobación automática (depósito confirmado)", "01", PEN, BCP, "En proceso", gc.nro("04417382")),
            ("Rojo: cuenta ajena", "04", PEN, BCP, "Rechazada", None),
            ("Rojo: comprobante duplicado", "05", PEN, BCP, "Rechazada", None),
        ]:
            id_op = operacion(token, cot, origen, DEST_USD, img[clave], numero)
            v, seg = esperar(id_op, token, "finalizada")
            reportar(nombre, id_op, v["estado_final"] == esperado and v["decidido_por"] == "agente",
                     f"{v['estado_final']} por {v['decidido_por']} en {seg:.0f} s" + (f" · {v['motivo']}" if v.get("motivo") else ""))

        # Depósito tardío: llega al banco mientras el workflow espera → se aprueba solo
        id_op = operacion(token, PEN, {"tipo": "banco", "banco": "Interbank"}, DEST_USD, img["10"])
        time.sleep(25)
        gc.registrar_depositos(API, BANCO_KEY, claves={"10"})
        v, seg = esperar(id_op, token, "finalizada")
        a = analisis(id_op)
        reportar("Verde tardío: el depósito llega durante la espera", id_op,
                 v["estado_final"] == "En proceso" and v["decidido_por"] == "agente",
                 f"{v['estado_final']} por {v['decidido_por']} en {seg:.0f} s · {a.get('conciliacion', {}).get('intento')} consulta(s) al banco")

        # Revisión humana
        for nombre, clave, cot, origen, destino, decision, esperado, numero, regla in [
            ("Amarillo: sin depósito en el banco → rechaza", "09", PEN, BCP, DEST_USD,
             {"decision": "rechazar", "motivo": "El depósito no llegó a la cuenta de NexoCambio."}, "Rechazada", None, "deposito_banco"),
            ("Amarillo: monto alto → aprueba", "06", USD, {"tipo": "banco", "banco": "Scotiabank"}, DEST_PEN,
             {"decision": "aprobar"}, "En proceso", None, None),
            ("Amarillo: monto distinto → rechaza", "03", PEN, BCP, DEST_USD,
             {"decision": "rechazar", "motivo": "El monto transferido no coincide con la operación."}, "Rechazada", None, "monto"),
            ("Amarillo: número declarado distinto → aprueba", "02", {**PEN, "monto_origen": 250},
             {"tipo": "banco", "banco": "Interbank"}, DEST_USD, {"decision": "aprobar"}, "En proceso", "11111111", "numero_declarado"),
        ]:
            id_op = operacion(token, cot, origen, destino, img[clave], numero)
            v, seg = esperar(id_op, token, "en_revision")
            a = analisis(id_op)
            falla = next((r for r in a.get("verificaciones", []) if r["regla"] == regla), {}) if regla else {}
            print(f"      revisión en {seg:.0f} s · {a.get('semaforo')} · {a.get('justificacion', '')[:160]}")
            s, r = llamar("POST", f"/validaciones/{id_op}/decision", decision, admin=True)
            assert s == 202, r
            v, _ = esperar(id_op, token, "finalizada")
            ok = (v["estado_final"] == esperado and v["decidido_por"] == "operador" and a.get("semaforo") == "amarillo"
                  and (not regla or falla.get("resultado") == "no_cumple"))
            reportar(nombre, id_op, ok, f"{v['estado_final']} por {v['decidido_por']}")
    print(json.dumps([{"escenario": n, "operacion": o, "ok": k, "detalle": d} for n, o, k, d in resultados], ensure_ascii=False))
    sys.exit(0 if all(r[2] for r in resultados) else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Prueba NexoGuard de punta a punta contra la API desplegada (los mismos escenarios que Postman, carpeta 6).

Uso:  python scripts/probar_nexoguard.py <ApiUrl>
Genera comprobantes con fecha de hoy y números nuevos, registra un cliente de prueba y recorre:
aprobación automática, rechazo por monto, rechazo por duplicado y revisión humana con decisión del operador.
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

API = sys.argv[1].rstrip("/")
ADMIN = (RAIZ / ".secrets" / "admin_key").read_text().strip()


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


def esperar(id_op, token, hasta, max_seg=240):
    t0 = time.time()
    while time.time() - t0 < max_seg:
        s, v = llamar("GET", f"/validaciones/{id_op}", token=token)
        if s == 200 and (v["estado"] == hasta or (hasta == "en_revision" and v["estado"] == "finalizada")):
            return v, time.time() - t0
        time.sleep(4)
    raise TimeoutError(f"{id_op} no llegó a {hasta}")


def operacion(token, cot, origen, destino, imagen):
    s, q = llamar("POST", "/cotizar", cot)
    assert s == 201, q
    s, op = llamar("POST", "/operaciones", {"id_cotizacion": q["id_cotizacion"], "origen": origen, "destino": destino}, token)
    assert s == 201, op
    s, r = llamar("POST", f"/operaciones/{op['id_operacion']}/comprobante",
                  {"nombre_archivo": imagen.name, "content_type": "image/png",
                   "contenido_base64": base64.b64encode(imagen.read_bytes()).decode()}, token)
    assert s == 200 and r["estado"] == "Pendiente de validación", r
    return op["id_operacion"]


def main():
    sufijo = random.randint(10_000_000, 99_999_999)
    cliente = {"tipo_cliente": "persona", "nombres": "Prueba", "apellidos": "NexoGuard", "tipo_documento": "DNI",
               "numero_documento": str(sufijo), "fecha_nacimiento": "1994-05-10", "telefono": "9" + str(sufijo),
               "ocupacion": "Dependiente", "pep": False, "correo": f"nexoguard{sufijo}@correo.com", "password": "Clave1234"}
    s, r = llamar("POST", "/registro", cliente)
    assert s == 201, r
    s, r = llamar("POST", "/login", {"correo": cliente["correo"], "password": "Clave1234"})
    token = r["token"]
    with tempfile.TemporaryDirectory() as tmp:
        img = {p.stem[:2]: p for p in gc.generar(Path(tmp), semilla=random.randint(1, 9_000_000)).glob("*.png")}
        pen = {"modalidad": "casa", "moneda_origen": "PEN", "moneda_destino": "USD", "monto_origen": 1000}
        bcp = {"tipo": "banco", "banco": "BCP"}
        dest = {"tipo": "banco", "banco": "Interbank", "tipo_cuenta": "Ahorros", "numero": "8983141592653", "titular": "Prueba NexoGuard"}
        resultados = []
        for nombre, clave, esperado in [("Aprobación automática", "01", "En proceso"),
                                        ("Rechazo automático: cuenta ajena", "04", "Rechazada"),
                                        ("Rechazo automático: duplicado", "05", "Rechazada")]:
            id_op = operacion(token, pen, bcp, dest, img[clave])
            v, seg = esperar(id_op, token, "finalizada")
            ok = v["estado_final"] == esperado and v["decidido_por"] == "agente"
            resultados.append((nombre, id_op, ok, f"{v['estado_final']} por {v['decidido_por']} en {seg:.0f} s"
                               + (f" · {v['motivo']}" if v.get("motivo") else "")))
            print(("OK  " if ok else "FALLA ") + resultados[-1][0], "·", resultados[-1][3], flush=True)

        usd = {"modalidad": "casa", "moneda_origen": "USD", "moneda_destino": "PEN", "monto_origen": 12000}
        dest_pen = {"tipo": "banco", "banco": "BCP", "tipo_cuenta": "Corriente", "numero": "19324587100391", "titular": "Prueba"}
        for nombre, args, decision, esperado in [
            ("Revisión humana: monto alto → aprueba", (usd, {"tipo": "banco", "banco": "Scotiabank"}, dest_pen, img["06"]),
             {"decision": "aprobar"}, "En proceso"),
            ("Revisión humana: monto distinto → rechaza", (pen, bcp, dest, img["03"]),
             {"decision": "rechazar", "motivo": "El monto transferido no coincide con la operación."}, "Rechazada"),
        ]:
            id_op = operacion(token, *args)
            v, seg = esperar(id_op, token, "en_revision")
            s, det = llamar("GET", f"/validaciones/{id_op}/admin", admin=True)
            a = det["validaciones"][0]
            print(f"     revisión en {seg:.0f} s · semáforo {a.get('semaforo')} · alerta {a.get('alerta_cumplimiento')} · {a.get('justificacion')}")
            s, r = llamar("POST", f"/validaciones/{id_op}/decision", decision, admin=True)
            assert s == 202, r
            v, seg = esperar(id_op, token, "finalizada")
            ok = v["estado_final"] == esperado and v["decidido_por"] == "operador" and a.get("semaforo") == "amarillo"
            resultados.append((nombre, id_op, ok, f"{v['estado_final']} por {v['decidido_por']}"))
            print(("OK  " if ok else "FALLA ") + nombre, "·", resultados[-1][3], flush=True)
    print(json.dumps([{"escenario": n, "operacion": o, "ok": k, "detalle": d} for n, o, k, d in resultados], ensure_ascii=False))
    sys.exit(0 if all(r[2] for r in resultados) else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Deja el entorno de AWS listo para la exposición de NexoGuard con un solo comando.

Uso:  python scripts/preparar_exposicion.py [--stack nexocambio-dev] [--semilla 101] [--ensayo] [--sin-postman]

1. Lee la ApiUrl y el tema SNS de las salidas del stack (y comprueba las credenciales del Learner Lab).
2. Reinicia los datos de prueba: validaciones, banco simulado, operaciones y comprobantes en S3 (los clientes quedan).
3. Regenera los comprobantes de tests/fixtures/comprobantes/ con la fecha de hoy.
4. Registra en el banco simulado los depósitos de los comprobantes legítimos y comprueba que el banco los tenga.
5. Regenera la carpeta 6 de la colección de Postman con comprobantes de hoy.
6. Comprueba que el tema SNS tenga una suscripción confirmada.
--ensayo: además ejecuta el caso 1 (verde) por la API, confirma que se aprueba solo y vuelve a dejar todo limpio
          (reinicia y registra otra vez los depósitos), para que el caso 1 de la demo también salga en verde.
"""
import base64
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import boto3

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import generar_comprobantes as gc  # noqa: E402

ADMIN = (RAIZ / ".secrets" / "admin_key").read_text().strip()
BANCO_KEY = (RAIZ / ".secrets" / "banco_key").read_text().strip()
ARGS = sys.argv[1:]
STACK = ARGS[ARGS.index("--stack") + 1] if "--stack" in ARGS else "nexocambio-dev"
SEMILLA = int(ARGS[ARGS.index("--semilla") + 1]) if "--semilla" in ARGS else 101
CON_DEPOSITO = {"01", "02", "03", "06", "07"}


def llamar(api, metodo, ruta, cuerpo=None, token=None, cabeceras=None):
    h = {"Content-Type": "application/json", **(cabeceras or {})}
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(api + ruta, method=metodo, headers=h,
                                 data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def paso(texto):
    print(f"\n▸ {texto}", flush=True)


def fallar(texto):
    print(f"  ✗ {texto}", flush=True)
    sys.exit(1)


def salidas_stack():
    try:
        boto3.client("sts").get_caller_identity()
    except Exception as e:  # noqa: BLE001
        fallar(f"Credenciales de AWS inválidas o vencidas ({type(e).__name__}). Actualizar ~/.aws/credentials.")
    try:
        pila = boto3.client("cloudformation").describe_stacks(StackName=STACK)["Stacks"][0]
    except Exception:  # noqa: BLE001
        fallar(f"No existe el stack {STACK}: desplegar primero con scripts/deploy.sh.")
    return {o["OutputKey"]: o["OutputValue"] for o in pila.get("Outputs", [])}


def reiniciar(api):
    s, r = llamar(api, "POST", "/demo/reiniciar", {"incluir_operaciones": True}, cabeceras={"x-admin-key": ADMIN})
    if s != 200 or "error" in r.get("banco", {}):
        fallar(f"El reinicio respondió {s}: {r}")
    ops = r.get("operaciones", {})
    print(f"  ✓ {r['ejecuciones_detenidas']} ejecuciones detenidas, {r['validaciones_borradas']} validaciones, "
          f"{r['banco']['borrados']} movimientos del banco y {ops.get('operaciones_borradas', 0)} operaciones borradas")


def registrar_y_comprobar(api):
    for k, numero, estado in gc.registrar_depositos(api, BANCO_KEY):
        if estado not in (201, 409):
            fallar(f"El depósito del comprobante {k} respondió HTTP {estado}")
    for k, (_, monto, moneda, numero, *_resto) in gc.depositos().items():
        if k not in CON_DEPOSITO:
            continue
        s, r = llamar(api, "GET", f"/banco/depositos?numero_operacion={numero}", cabeceras={"x-banco-key": BANCO_KEY})
        if s != 200 or not r.get("total"):
            fallar(f"El banco no tiene el depósito del comprobante {k} (N° {numero})")
        print(f"  ✓ comprobante {k}: depósito {moneda} {monto:,} con N° {numero} en el banco")


def ensayo(api):
    """Caso 1 del guion por la API, con los mismos datos que se ingresan en la web."""
    s, login = llamar(api, "POST", "/login", {"correo": "demo@nexocambio.pe", "password": "Demo1234"})
    if s != 200:
        fallar(f"No se pudo iniciar sesión con el cliente demo: {login}")
    token = login["token"]
    s, q = llamar(api, "POST", "/cotizar", {"modalidad": "casa", "moneda_origen": "PEN", "moneda_destino": "USD",
                                            "monto_origen": 1000})
    s, op = llamar(api, "POST", "/operaciones", {
        "id_cotizacion": q["id_cotizacion"], "origen": {"tipo": "banco", "banco": "BCP"},
        "destino": {"tipo": "banco", "banco": "Interbank", "tipo_cuenta": "Ahorros", "numero": "8983141592653",
                    "titular": "Cliente Demo"}}, token)
    imagen = gc.SALIDA / "01_ok_bcp_pen_1000.png"
    s, r = llamar(api, "POST", f"/operaciones/{op['id_operacion']}/comprobante", {
        "nombre_archivo": imagen.name, "content_type": "image/png",
        "contenido_base64": base64.b64encode(imagen.read_bytes()).decode()}, token)
    if s != 200:
        fallar(f"No se pudo adjuntar el comprobante: {r}")
    t0 = time.time()
    while time.time() - t0 < 240:
        time.sleep(4)
        s, v = llamar(api, "GET", f"/validaciones/{op['id_operacion']}", token=token)
        if s == 200 and v["estado"] != "en_curso":
            break
    if v.get("estado_final") != "En proceso" or v.get("decidido_por") != "agente":
        fallar(f"El caso 1 no salió en verde ({v.get('estado')}, {v.get('motivo')}). Revisar antes de exponer.")
    print(f"  ✓ caso 1 aprobado automáticamente en {time.time() - t0:.0f} s ({op['id_operacion']})")


def comprobar_correo(tema):
    subs = boto3.client("sns").list_subscriptions_by_topic(TopicArn=tema)["Subscriptions"]
    confirmadas = [s["Endpoint"] for s in subs if s["SubscriptionArn"].startswith("arn:")]
    if confirmadas:
        print(f"  ✓ avisos de NexoGuard a: {', '.join(confirmadas)}")
    else:
        print("  ! el tema SNS no tiene suscripciones confirmadas: no llegarán correos de revisión")


def main():
    paso(f"Stack {STACK}")
    out = salidas_stack()
    api = out["ApiUrl"].rstrip("/")
    print(f"  ✓ API {api}\n  ✓ Web {out.get('SitioWebHttpsUrl', '')}")

    paso("Reiniciar los datos de prueba")
    reiniciar(api)

    paso(f"Comprobantes con fecha {date.today():%d-%m-%Y} (semilla {SEMILLA})")
    gc.generar(gc.SALIDA, semilla=SEMILLA)
    print(f"  ✓ 10 imágenes en {gc.SALIDA.relative_to(RAIZ)}")

    paso("Depósitos en el banco simulado")
    registrar_y_comprobar(api)

    if "--ensayo" in ARGS:
        paso("Ensayo del caso 1 (verde)")
        ensayo(api)
        paso("Dejar todo limpio otra vez después del ensayo")
        reiniciar(api)
        registrar_y_comprobar(api)

    if "--sin-postman" not in ARGS:
        paso("Colección de Postman (carpeta 6)")
        subprocess.run([sys.executable, str(RAIZ / "postman" / "generar_nexoguard.py")], check=True)
        print("  ✓ volver a importar postman/NexoCambio.postman_collection.json en Postman")

    paso("Correo de NexoGuard (SNS)")
    comprobar_correo(out["TemaNexoGuard"])

    print(f"""
Listo para exponer. El caso 1 (01_ok_bcp_pen_1000.png) saldrá en verde.
  · No usar «Reiniciar datos de prueba» ni la 6.0 de Postman antes de la demo web: borran los depósitos.
    Si hace falta reiniciar, volver a ejecutar este script.
  · Caso 9 (depósito tardío), dentro de los 2 min siguientes a subir el comprobante:
    python scripts/generar_comprobantes.py --semilla {SEMILLA} --deposito-tardio {api}""")


if __name__ == "__main__":
    main()

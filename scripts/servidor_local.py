#!/usr/bin/env python3
"""
Servidor local de NexoCambio: ejecuta los 3 microservicios reales (mismo código que
las Lambdas) sobre un AWS simulado con moto, detrás de un servidor HTTP con CORS.

Sirve para: probar el frontend y Postman SIN desplegar en AWS, y ensayar la demo.
No requiere credenciales ni internet.

    pip install "moto[dynamodb,s3]" boto3
    python scripts/servidor_local.py            # http://localhost:8787
    python scripts/servidor_local.py --sin-datos-demo

Los datos viven en memoria: se pierden al detener el servidor.
"""
import argparse
import importlib.util
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "layer" / "python"))

ENTORNO = {
    "AWS_ACCESS_KEY_ID": "local", "AWS_SECRET_ACCESS_KEY": "local", "AWS_DEFAULT_REGION": "us-east-1",
    "TABLE_CLIENTES": "nexo-local-clientes", "TABLE_COTIZACIONES": "nexo-local-cotizaciones",
    "TABLE_TASAS": "nexo-local-tasas", "TABLE_OPERACIONES": "nexo-local-operaciones",
    "BUCKET_COMPROBANTES": "nexo-local-comprobantes", "FN_COTIZACIONES": "local",
    "JWT_SECRET": "secreto-local-solo-para-pruebas-0123456789", "ADMIN_KEY": "admin-local",
}
for k, v in ENTORNO.items():
    os.environ.setdefault(k, v)
os.environ.setdefault("USAR_TASAS_EN_VIVO", "false")

import boto3  # noqa: E402
from moto import mock_aws  # noqa: E402

PNG_1X1 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


def cargar(nombre):
    spec = importlib.util.spec_from_file_location(f"app_{nombre}", RAIZ / "services" / nombre / "app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def crear_infraestructura():
    db = boto3.client("dynamodb")
    def tabla(nombre, pk, extra_attrs=(), gsi=None):
        attrs = [{"AttributeName": pk, "AttributeType": "S"}] + [{"AttributeName": a, "AttributeType": "S"} for a in extra_attrs]
        kw = dict(TableName=nombre, BillingMode="PAY_PER_REQUEST", AttributeDefinitions=attrs,
                  KeySchema=[{"AttributeName": pk, "KeyType": "HASH"}])
        if gsi:
            kw["GlobalSecondaryIndexes"] = gsi
        db.create_table(**kw)
    tabla(os.environ["TABLE_CLIENTES"], "pk")
    tabla(os.environ["TABLE_COTIZACIONES"], "id_cotizacion")
    tabla(os.environ["TABLE_TASAS"], "moneda")
    tabla(os.environ["TABLE_OPERACIONES"], "id_operacion", ("id_cliente", "fecha_operacion"), [{
        "IndexName": "cliente-fecha-index", "Projection": {"ProjectionType": "ALL"},
        "KeySchema": [{"AttributeName": "id_cliente", "KeyType": "HASH"}, {"AttributeName": "fecha_operacion", "KeyType": "RANGE"}]}])
    boto3.client("s3").create_bucket(Bucket=os.environ["BUCKET_COMPROBANTES"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", type=int, default=8787)
    ap.add_argument("--sin-datos-demo", action="store_true")
    args = ap.parse_args()

    with mock_aws():
        crear_infraestructura()
        cot, cli, ops = cargar("cotizaciones"), cargar("clientes"), cargar("operaciones")

        def via_lambda(id_cotizacion):  # sustituye Lambda→Lambda por una llamada directa
            from nexo_common import ApiError
            r = cot.handler({"accion": "obtener", "id_cotizacion": id_cotizacion})
            if not r["ok"]:
                raise ApiError(404, r["mensaje"], "cotizacion_no_encontrada")
            return r["cotizacion"]
        ops.cotizaciones_obtener = via_lambda

        rutas = [  # (método, patrón, routeKey, módulo, nombres de parámetros)
            ("POST", r"^/cotizar$", "POST /cotizar", cot, ()),
            ("POST", r"^/registro$", "POST /registro", cli, ()),
            ("POST", r"^/login$", "POST /login", cli, ()),
            ("GET", r"^/clientes/([^/]+)$", "GET /clientes/{id_cliente}", cli, ("id_cliente",)),
            ("POST", r"^/operaciones$", "POST /operaciones", ops, ()),
            ("GET", r"^/operaciones$", "GET /operaciones", ops, ()),
            # las rutas literales de back-office van antes que "{id_operacion}" (el matching es lineal, no por especificidad)
            ("GET", r"^/operaciones/admin$", "GET /operaciones/admin", ops, ()),
            ("GET", r"^/operaciones/([^/]+)/admin$", "GET /operaciones/{id_operacion}/admin", ops, ("id_operacion",)),
            ("GET", r"^/operaciones/([^/]+)$", "GET /operaciones/{id_operacion}", ops, ("id_operacion",)),
            ("POST", r"^/operaciones/([^/]+)/comprobante$", "POST /operaciones/{id_operacion}/comprobante", ops, ("id_operacion",)),
            ("PATCH", r"^/operaciones/([^/]+)/estado$", "PATCH /operaciones/{id_operacion}/estado", ops, ("id_operacion",)),
        ]

        def invocar(metodo, ruta, headers, cuerpo):
            for m, patron, key, modulo, nombres in rutas:
                mt = re.match(patron, ruta)
                if m == metodo and mt:
                    ev = {"routeKey": key, "rawPath": ruta, "headers": {k.lower(): v for k, v in headers.items()},
                          "pathParameters": dict(zip(nombres, mt.groups())), "body": cuerpo or None,
                          "isBase64Encoded": False, "requestContext": {"http": {"method": metodo}}}
                    return modulo.handler(ev)
            return {"statusCode": 404, "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"message": "Not Found"})}

        if not args.sin_datos_demo:
            sembrar(cli, ops, invocar)

        class H(BaseHTTPRequestHandler):
            def _cors(self):
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "content-type, authorization, x-admin-key")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")

            def _atender(self):
                n = int(self.headers.get("Content-Length") or 0)
                cuerpo = self.rfile.read(n).decode() if n else ""
                r = invocar(self.command, urlparse(self.path).path.rstrip("/") or "/", dict(self.headers), cuerpo)
                datos = r["body"].encode()
                self.send_response(r["statusCode"])
                for k, v in r.get("headers", {}).items():
                    self.send_header(k, v)
                self._cors()
                self.send_header("Content-Length", str(len(datos)))
                self.end_headers()
                self.wfile.write(datos)

            do_GET = do_POST = do_PATCH = _atender

            def do_OPTIONS(self):
                self.send_response(204); self._cors(); self.send_header("Content-Length", "0"); self.end_headers()

            def log_message(self, fmt, *a):
                sys.stderr.write(f"[local] {self.command} {self.path} → {a[1] if len(a) > 1 else ''}\n")

        srv = HTTPServer(("127.0.0.1", args.puerto), H)
        print(f"NexoCambio local listo en http://localhost:{args.puerto}  (Ctrl+C para salir)", flush=True)
        if not args.sin_datos_demo:
            print("  Cliente demo: demo@nexocambio.pe / Demo1234   ·   x-admin-key: " + os.environ["ADMIN_KEY"], flush=True)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass


def sembrar(cli, ops, invocar):
    """Cliente demo + 3 operaciones en distintos estados (para ensayar la exposición)."""
    j = lambda r: json.loads(r["body"])
    hdr = {"content-type": "application/json"}
    invocar("POST", "/registro", hdr, json.dumps({
        "tipo_cliente": "persona", "nombres": "Lucía", "apellidos": "Ramírez Torres", "tipo_documento": "DNI",
        "numero_documento": "45879632", "fecha_nacimiento": "1994-05-10", "telefono": "987654321",
        "ocupacion": "Dependiente", "pep": False, "correo": "demo@nexocambio.pe", "password": "Demo1234"}))
    tk = j(invocar("POST", "/login", hdr, json.dumps({"correo": "demo@nexocambio.pe", "password": "Demo1234"})))["token"]
    auth = {**hdr, "authorization": f"Bearer {tk}"}
    admin = {**hdr, "x-admin-key": os.environ["ADMIN_KEY"]}
    dest = {"tipo": "banco", "banco": "Interbank", "tipo_cuenta": "Ahorros", "numero": "8983141592653", "titular": "Lucía Ramírez Torres"}
    for monto, pares in ((3400, ["En proceso", "Procesada"]), (500, ["Rechazada"]), (800, ["En proceso"]), (250, [])):
        q = j(invocar("POST", "/cotizar", hdr, json.dumps({"modalidad": "casa", "moneda_origen": "PEN", "moneda_destino": "USD", "monto_origen": monto})))
        op = j(invocar("POST", "/operaciones", auth, json.dumps({"id_cotizacion": q["id_cotizacion"], "origen": {"tipo": "banco", "banco": "BCP"}, "destino": dest})))
        p = f"/operaciones/{op['id_operacion']}"
        invocar("POST", p + "/comprobante", auth, json.dumps({"nombre_archivo": "comprobante.png", "content_type": "image/png", "contenido_base64": PNG_1X1, "numero_transferencia": str(100000 + monto)}))
        for est in pares:
            extra = {"motivo_rechazo": "El monto transferido (S/ 450.00) no coincide con el de la operación."} if est == "Rechazada" else {}
            invocar("PATCH", p + "/estado", admin, json.dumps({"estado": est, **extra}))


if __name__ == "__main__":
    main()

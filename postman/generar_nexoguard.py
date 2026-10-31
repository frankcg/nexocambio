#!/usr/bin/env python3
"""Agrega (o reemplaza) la carpeta «6. NexoGuard» en NexoCambio.postman_collection.json.

Cada ejecución regenera los comprobantes ficticios con la fecha de HOY y números de operación
NUEVOS (semilla aleatoria) y los incrusta en base64: así la colección puede correrse de nuevo sin
que la detección de duplicados de NexoGuard rechace la aprobación automática.

Uso:  python postman/generar_nexoguard.py [--semilla N]
Luego, en Postman: Run collection (o las carpetas 2 y 6) contra la API desplegada en AWS.
"""
import base64
import json
import random
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import generar_comprobantes as gc  # noqa: E402

COLECCION = RAIZ / "postman" / "NexoCambio.postman_collection.json"
NOMBRE = "6. NexoGuard (workflow agéntico · AWS + Groq)"
ESPERA_MS = 4000
MAX_INTENTOS = 45   # ~3 min: con la capa gratuita de Groq (~3 imágenes/min) el workflow reintenta ante 429

DESCRIPCION = (
    "Prueba el workflow NexoGuard de punta a punta contra la API desplegada en AWS (requiere Step Functions y "
    "la clave de Groq). Antes, ejecutar la carpeta 2 (registro y login) para tener {{token}}.\n\n"
    "Cada escenario: cotiza → registra la operación → adjunta un comprobante ficticio → espera el resultado "
    "consultando GET /validaciones/{id} cada 4 s (usar el Collection Runner: la espera usa setNextRequest).\n\n"
    "Regenerar antes de cada corrida: `python postman/generar_nexoguard.py` (números de operación nuevos).")


def b64(ruta: Path) -> str:
    return base64.b64encode(ruta.read_bytes()).decode()


def url(ruta: str) -> dict:
    camino, _, consulta = ruta.partition("?")
    partes = [p for p in camino.split("/") if p]
    u = {"raw": "{{baseUrl}}/" + "/".join(partes) + (f"?{consulta}" if consulta else ""),
         "host": ["{{baseUrl}}"], "path": partes}
    if consulta:
        u["query"] = [dict(zip(("key", "value"), q.split("=", 1))) for q in consulta.split("&")]
    return u


def req(nombre, metodo, ruta, cuerpo=None, tests=(), pre=(), token=True, admin=False, desc=""):
    headers = [{"key": "Content-Type", "value": "application/json"}] if cuerpo is not None else []
    if token:
        headers.append({"key": "Authorization", "value": "Bearer {{token}}"})
    if admin:
        headers.append({"key": "x-admin-key", "value": "{{adminKey}}"})
    item = {"name": nombre, "event": [], "request": {"method": metodo, "header": headers, "url": url(ruta), "description": desc}}
    if pre:
        item["event"].append({"listen": "prerequest", "script": {"type": "text/javascript", "exec": list(pre)}})
    if tests:
        item["event"].append({"listen": "test", "script": {"type": "text/javascript", "exec": list(tests)}})
    if cuerpo is not None:
        item["request"]["body"] = {"mode": "raw", "raw": json.dumps(cuerpo, ensure_ascii=False, indent=2),
                                   "options": {"raw": {"language": "json"}}}
    return item


def esperar(nombre, var_op, hasta, tests):
    """GET /validaciones/{id} repetido (setNextRequest) mientras el estado no sea el esperado."""
    condicion = "v.estado === 'en_curso'" if hasta == "en_revision" else "v.estado !== 'finalizada'"
    return req(nombre, "GET", f"/validaciones/{{{{{var_op}}}}}", pre=[f"setTimeout(() => {{}}, {ESPERA_MS});"], tests=[
        "const v = pm.response.code === 200 ? pm.response.json() : { estado: 'en_curso' };",
        "const n = Number(pm.collectionVariables.get('ng_intentos') || 0) + 1;",
        f"if (({condicion}) && n < {MAX_INTENTOS}) {{",
        "  pm.collectionVariables.set('ng_intentos', n);",
        "  console.log(`NexoGuard: intento ${n}, estado ${v.estado}`);",
        "  (pm.execution && pm.execution.setNextRequest ? pm.execution : postman).setNextRequest(pm.info.requestName);",
        "} else {",
        "  pm.collectionVariables.set('ng_intentos', 0);",
        "  pm.test('Status 200', () => pm.response.to.have.status(200));",
        *[f"  {t}" for t in tests],
        "}",
    ], desc=f"Espera hasta {hasta} (máx. {MAX_INTENTOS} consultas cada {ESPERA_MS // 1000} s).")


def pref(var: str) -> str:
    """ng1_op → 6.1 (prefijo legible para los nombres de los requests)."""
    return f"6.{var[2]}"


def escenario(n, titulo, cotizacion, origen, destino, imagen, var, resultado_tests, extra=(), numero=None):
    vc, vo = f"{n}_cot", f"{n}_op"
    items = [
        req(f"{pref(n)}.1 Cotizar", "POST", "/cotizar", cotizacion, token=False, tests=[
            "pm.test('Status 201', () => pm.response.to.have.status(201));",
            f"pm.collectionVariables.set('{vc}', pm.response.json().id_cotizacion);"]),
        req(f"{pref(n)}.2 Registrar operación", "POST", "/operaciones",
            {"id_cotizacion": f"{{{{{vc}}}}}", "origen": origen, "destino": destino}, tests=[
                "pm.test('Status 201', () => pm.response.to.have.status(201));",
                f"pm.collectionVariables.set('{vo}', pm.response.json().id_operacion);"]),
        req(f"{pref(n)}.3 Adjuntar comprobante (inicia NexoGuard)", "POST", f"/operaciones/{{{{{vo}}}}}/comprobante",
            {"nombre_archivo": imagen.name, "content_type": "image/png", "contenido_base64": b64(imagen),
             **({"numero_transferencia": numero} if numero else {})}, tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "pm.test('Queda pendiente de validación', () => pm.expect(pm.response.json().estado).to.eql('Pendiente de validación'));",
                "pm.collectionVariables.set('ng_intentos', 0);"],
            desc=f"Comprobante ficticio: {imagen.name}" + (f" · número declarado {numero}" if numero else "")),
        *resultado_tests(vo),
        *extra,
    ]
    return {"name": titulo, "item": items}


def construir(carpeta: Path) -> dict:
    img = {p.stem[:2]: p for p in carpeta.glob("*.png")}
    pen_usd = {"modalidad": "casa", "moneda_origen": "PEN", "moneda_destino": "USD", "monto_origen": 1000}
    bcp = {"tipo": "banco", "banco": "BCP"}
    dest_usd = {"tipo": "banco", "banco": "Interbank", "tipo_cuenta": "Ahorros", "numero": "8983141592653", "titular": "Lucía Ramírez"}

    def final(estado, por, *mas):
        return lambda vo: [
            esperar(f"{pref(vo)} · Esperar resultado de NexoGuard", vo, "finalizada", [
                f"pm.test('Resultado: {estado}', () => pm.expect(v.estado_final).to.eql('{estado}'));",
                f"pm.test('Decidido por: {por}', () => pm.expect(v.decidido_por).to.eql('{por}'));", *mas]),
            req(f"{pref(vo)} · El cliente ve el resultado", "GET", f"/operaciones/{{{{{vo}}}}}", tests=[
                f"const o = pm.response.json();",
                f"pm.test('Estado {estado}', () => pm.expect(o.estado).to.eql('{estado}'));",
                f"pm.test('El historial registra al {por}', () => pm.expect(o.historial[o.historial.length - 1].actor).to.eql('{por}'));"]),
        ]

    def revision(analisis, decision, estado_final, con_errores=False):
        """Espera la revisión, consulta la cola y el análisis del agente, y el operador decide."""
        def pasos(vo):
            errores = [
                req(f"{pref(vo)} · Decisión - error: sin clave de back-office", "POST", f"/validaciones/{{{{{vo}}}}}/decision",
                    {"decision": "aprobar"}, token=False, tests=["pm.test('Status 403', () => pm.response.to.have.status(403));"]),
                req(f"{pref(vo)} · Decisión - error: rechazar sin motivo", "POST", f"/validaciones/{{{{{vo}}}}}/decision",
                    {"decision": "rechazar"}, token=False, admin=True, tests=["pm.test('Status 400', () => pm.response.to.have.status(400));"]),
            ] if con_errores else []
            ya_decidida = [
                req(f"{pref(vo)} · Decisión - error: ya decidida", "POST", f"/validaciones/{{{{{vo}}}}}/decision",
                    {"decision": "rechazar", "motivo": "Intento duplicado"}, token=False, admin=True,
                    tests=["pm.test('Status 409', () => pm.response.to.have.status(409));"]),
            ] if con_errores else []
            texto = "aprobar" if decision["decision"] == "aprobar" else "rechazar con motivo"
            return [
                esperar(f"{pref(vo)} · Esperar a que pase a revisión", vo, "en_revision", [
                    "pm.test('Va a revisión humana', () => pm.expect(v.estado).to.eql('en_revision'));"]),
                req(f"{pref(vo)} · Back-office: cola de revisión", "GET", "/validaciones/admin?estado=en_revision", token=False, admin=True, tests=[
                    "pm.test('Status 200', () => pm.response.to.have.status(200));",
                    f"pm.test('La operación está en la cola', () => pm.expect(pm.response.json().validaciones.map(x => x.id_operacion)).to.include(pm.collectionVariables.get('{vo}')));",
                    "pm.test('El token nunca sale de la API', () => pm.response.json().validaciones.forEach(x => pm.expect(x).to.not.have.property('task_token')));"]),
                req(f"{pref(vo)} · Back-office: análisis del agente", "GET", f"/validaciones/{{{{{vo}}}}}/admin", token=False, admin=True, tests=[
                    "const v = pm.response.json().validaciones[0];",
                    "pm.test('Semáforo amarillo', () => pm.expect(v.semaforo).to.eql('amarillo'));",
                    "pm.test('Incluye verificaciones y justificación', () => { pm.expect(v.verificaciones).to.be.an('array').that.is.not.empty; pm.expect(v.justificacion).to.be.a('string'); });",
                    *analisis]),
                *errores,
                req(f"{pref(vo)} · Decisión del operador: {texto}", "POST", f"/validaciones/{{{{{vo}}}}}/decision",
                    decision, token=False, admin=True, tests=[
                        "pm.test('Status 202', () => pm.response.to.have.status(202));",
                        "pm.collectionVariables.set('ng_intentos', 0);"],
                    desc="Reanuda el workflow (SendTaskSuccess con el task token guardado)."),
                *ya_decidida,
                *final(estado_final, "operador")(vo),
            ]
        return pasos

    return {
        "name": NOMBRE, "description": DESCRIPCION,
        "item": [
            escenario("ng1", "6.1 Aprobación automática (verde)", pen_usd, bcp, dest_usd, img["01"], "ng1",
                      final("En proceso", "agente"), numero=gc.nro("04417382")),
            escenario("ng2", "6.2 Rechazo automático: cuenta ajena (rojo)", pen_usd, bcp, dest_usd, img["04"], "ng2",
                      final("Rechazada", "agente", "pm.test('Motivo: no es una cuenta de NexoCambio', () => pm.expect(v.motivo).to.include('no es una cuenta de NexoCambio'));")),
            escenario("ng3", "6.3 Rechazo automático: comprobante duplicado (rojo)", pen_usd, bcp, dest_usd, img["05"], "ng3",
                      final("Rechazada", "agente", "pm.test('Motivo: número ya usado', () => pm.expect(v.motivo).to.include('ya se usó'));")),
            escenario("ng4", "6.4 Revisión humana: monto alto (amarillo) → el operador aprueba",
                      {"modalidad": "casa", "moneda_origen": "USD", "moneda_destino": "PEN", "monto_origen": 12000},
                      {"tipo": "banco", "banco": "Scotiabank"},
                      {"tipo": "banco", "banco": "BCP", "tipo_cuenta": "Corriente", "numero": "19324587100391", "titular": "Importaciones del Sur"},
                      img["06"], "ng4",
                      revision(["pm.test('Alerta de cumplimiento (monto ≥ umbral)', () => pm.expect(v.alerta_cumplimiento).to.eql(true));",
                                "pm.test('Leyó US$ 12,000', () => pm.expect(v.extraccion.monto).to.eql(12000));"],
                               {"decision": "aprobar"}, "En proceso", con_errores=True)),
            escenario("ng5", "6.5 Revisión humana: monto distinto (amarillo) → el operador rechaza", pen_usd, bcp, dest_usd, img["03"], "ng5",
                      revision(["pm.test('La regla de monto no se cumple', () => pm.expect(v.verificaciones.find(r => r.regla === 'monto').resultado).to.eql('no_cumple'));",
                                "pm.test('Leyó S/ 850', () => pm.expect(v.extraccion.monto).to.eql(850));"],
                               {"decision": "rechazar", "motivo": "El monto transferido (S/ 850.00) no coincide con la operación (S/ 1,000.00)."},
                               "Rechazada")),
            escenario("ng6", "6.6 Revisión humana: número declarado distinto (amarillo) → el operador aprueba",
                      {**pen_usd, "monto_origen": 250}, {"tipo": "banco", "banco": "Interbank"}, dest_usd, img["02"], "ng6",
                      revision(["pm.test('El número declarado no coincide', () => pm.expect(v.verificaciones.find(r => r.regla === 'numero_declarado').resultado).to.eql('no_cumple'));"],
                               {"decision": "aprobar"}, "En proceso"),
                      numero="11111111"),
            {"name": "6.7 Errores de la API Validaciones", "item": [
                req("Validación - error: sin token", "GET", "/validaciones/{{ng1_op}}", token=False,
                    tests=["pm.test('Status 401', () => pm.response.to.have.status(401));"]),
                req("Validación - error: operación sin validación", "GET", "/validaciones/NX-NO-EXISTE",
                    tests=["pm.test('Status 404', () => pm.response.to.have.status(404));"]),
                req("Cola de revisión - error: sin clave", "GET", "/validaciones/admin", token=False,
                    tests=["pm.test('Status 403', () => pm.response.to.have.status(403));"]),
            ]},
        ],
    }


def main():
    args = sys.argv[1:]
    semilla = int(args[args.index("--semilla") + 1]) if "--semilla" in args else random.randint(1, 9_000_000)
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = gc.generar(Path(tmp), semilla=semilla)
        nueva = construir(carpeta)
    col = json.loads(COLECCION.read_text(encoding="utf-8"))
    col["item"] = [i for i in col["item"] if not i["name"].startswith("6. NexoGuard")] + [nueva]
    claves = {v["key"] for v in col.get("variable", [])}
    for k in ["ng_intentos"] + [f"ng{i}_{s}" for i in range(1, 7) for s in ("cot", "op")]:
        if k not in claves:
            col.setdefault("variable", []).append({"key": k, "value": ""})
    COLECCION.write_text(json.dumps(col, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(len(e.get("item", [])) for e in nueva["item"])
    print(f"Carpeta «{NOMBRE}» con {total} requests (semilla {semilla}) → {COLECCION.name}")


if __name__ == "__main__":
    main()

import base64
import time

import boto3
import pytest

from conftest import PERSONA, PNG_1X1, cuerpo, evento
import nexo_common as nc

CT = "nexo-test-cotizaciones"


def sesion(cli, correo="lucia@correo.com", datos=None):
    cli.handler(evento("POST /registro", datos or PERSONA))
    return cuerpo(cli.handler(evento("POST /login", {"correo": correo, "password": (datos or PERSONA)["password"]})))["token"]


def hacer_cotizacion(cot, **kw):
    base = {"modalidad": "casa", "moneda_origen": "PEN", "moneda_destino": "USD", "monto_origen": 1000}
    return cuerpo(cot.handler(evento("POST /cotizar", {**base, **kw})))


BANCO_ORIGEN = {"tipo": "banco", "banco": "BCP"}
BANCO_DESTINO = {"tipo": "banco", "banco": "Interbank", "tipo_cuenta": "Ahorros", "numero": "8983141592653", "titular": "Lucía Ramírez"}


def crear(ops, token, q, **kw):
    body = {"id_cotizacion": q["id_cotizacion"], "modalidad": q["modalidad"], "moneda_origen": q["moneda_origen"],
            "moneda_destino": q["moneda_destino"], "monto_origen": q["monto_origen"], "monto_destino": q["monto_destino"],
            "tasa": q["tasa"], "origen": BANCO_ORIGEN, "destino": BANCO_DESTINO, **kw}
    return ops.handler(evento("POST /operaciones", body, token))


def subir(ops, token, id_op, **kw):
    body = {"nombre_archivo": "yape.png", "content_type": "image/png", "contenido_base64": PNG_1X1,
            "numero_transferencia": "123456", **kw}
    return ops.handler(evento("POST /operaciones/{id_operacion}/comprobante", body, token, {"id_operacion": id_op}))


def test_flujo_completo_del_mvp(cli, cot, ops):
    tk = sesion(cli)
    q = hacer_cotizacion(cot)
    r = crear(ops, tk, q)
    op = cuerpo(r)
    assert r["statusCode"] == 201 and op["id_operacion"] == "NX-" + q["id_cotizacion"][4:]
    assert op["estado"] == "Pendiente de comprobante"

    r = subir(ops, tk, op["id_operacion"])
    assert r["statusCode"] == 200
    assert cuerpo(r)["estado"] == "Pendiente de validación" and cuerpo(r)["comprobante_nombre"] == "yape.png"
    assert len(cuerpo(r)["historial"]) == 1

    lista = cuerpo(ops.handler(evento("GET /operaciones", token=tk)))
    assert lista["total"] == 1 and lista["operaciones"][0]["estado"] == "Pendiente de validación"

    det = cuerpo(ops.handler(evento("GET /operaciones/{id_operacion}", token=tk, params={"id_operacion": op["id_operacion"]})))
    assert det["comprobante_url"].startswith("https://") and "X-Amz-Signature" in det["comprobante_url"]
    obj = boto3.client("s3").get_object(Bucket="nexo-test-comprobantes",
                                        Key=f"comprobantes/{det['id_cliente']}/{op['id_operacion']}/yape.png")
    assert obj["ServerSideEncryption"] == "AES256" and obj["Body"].read() == base64.b64decode(PNG_1X1)


def test_lista_vacia_y_no_incluye_borradores(cli, cot, ops):
    tk = sesion(cli)
    assert cuerpo(ops.handler(evento("GET /operaciones", token=tk))) == {"operaciones": [], "total": 0}
    crear(ops, tk, hacer_cotizacion(cot))  # queda sin comprobante → no se lista
    assert cuerpo(ops.handler(evento("GET /operaciones", token=tk)))["total"] == 0


def test_lista_ordenada_de_la_mas_reciente_a_la_mas_antigua(cli, cot, ops):
    tk = sesion(cli)
    ids = []
    for m in (100, 200, 300):
        q = hacer_cotizacion(cot, monto_origen=m)
        op = cuerpo(crear(ops, tk, q)); ids.append(op["id_operacion"])
        subir(ops, tk, op["id_operacion"]); time.sleep(0.01)
    lista = cuerpo(ops.handler(evento("GET /operaciones", token=tk)))["operaciones"]
    assert [o["id_operacion"] for o in lista] == ids[::-1]


def test_el_servidor_no_confia_en_la_tasa_ni_en_los_montos_del_navegador(cli, cot, ops):
    tk = sesion(cli)
    q = hacer_cotizacion(cot)
    op = cuerpo(crear(ops, tk, q, tasa=99, monto_destino=999999))
    assert op["tasa"] == pytest.approx(q["tasa"]) and op["monto_destino"] == pytest.approx(q["monto_destino"])
    # pero si cambia la moneda o el monto respecto de lo cotizado se rechaza
    q2 = hacer_cotizacion(cot)
    assert crear(ops, tk, q2, moneda_destino="EUR")["statusCode"] == 422
    assert crear(ops, tk, q2, monto_origen=50000)["statusCode"] == 422


def test_una_cotizacion_solo_puede_usarse_una_vez(cli, cot, ops):
    tk = sesion(cli)
    q = hacer_cotizacion(cot)
    assert crear(ops, tk, q)["statusCode"] == 201
    r = crear(ops, tk, q)
    assert r["statusCode"] == 409 and cuerpo(r)["codigo"] == "cotizacion_usada"


def test_cotizacion_vencida_o_inexistente(cli, cot, ops):
    tk = sesion(cli)
    q = hacer_cotizacion(cot)
    boto3.resource("dynamodb").Table(CT).update_item(
        Key={"id_cotizacion": q["id_cotizacion"]}, UpdateExpression="SET expira_epoch = :e",
        ExpressionAttributeValues={":e": int(time.time()) - 3600})
    r = crear(ops, tk, q)
    assert r["statusCode"] == 409 and cuerpo(r)["codigo"] == "cotizacion_expirada"
    q["id_cotizacion"] = "COT-NOEXISTE"
    assert crear(ops, tk, q)["statusCode"] == 404


@pytest.mark.parametrize("destino,codigo", [
    ({"tipo": "wallet", "red": "Bitcoin", "direccion": "x" * 30}, "extremo_invalido"),
    ({**BANCO_DESTINO, "numero": "123"}, "cuenta_invalida"),
    ({**BANCO_DESTINO, "banco": "Banco Fantasma"}, "banco_invalido"),
    ({**BANCO_DESTINO, "tipo_cuenta": "Vista"}, "tipo_cuenta_invalido"),
])
def test_validacion_de_cuentas(cli, cot, ops, destino, codigo):
    tk = sesion(cli)
    r = crear(ops, tk, hacer_cotizacion(cot), destino=destino)
    assert r["statusCode"] == 422 and cuerpo(r)["codigo"] == codigo


def test_operacion_cripto_con_wallet(cli, cot, ops):
    tk = sesion(cli)
    q = hacer_cotizacion(cot, modalidad="cripto", moneda_destino="USDT")
    dest = {"tipo": "wallet", "red": "TRON (TRC20)", "direccion": "TNxDemoC4mb1oU7k9QeR2sWp6YhL3vB8aZ"}
    r = crear(ops, tk, q, destino=dest)
    assert r["statusCode"] == 201 and cuerpo(r)["destino"]["red"] == "TRON (TRC20)"
    q2 = hacer_cotizacion(cot, modalidad="cripto", moneda_destino="USDT")
    assert crear(ops, tk, q2, destino={**dest, "red": "Solana"})["statusCode"] == 422  # Solana no está habilitada para USDT


def test_seguridad_sin_token_y_aislamiento_entre_clientes(cli, cot, ops):
    tk = sesion(cli)
    otro = sesion(cli, "otro@correo.com", {**PERSONA, "correo": "otro@correo.com", "numero_documento": "70000001"})
    op = cuerpo(crear(ops, tk, hacer_cotizacion(cot)))
    subir(ops, tk, op["id_operacion"])
    assert ops.handler(evento("GET /operaciones"))["statusCode"] == 401
    assert ops.handler(evento("GET /operaciones", token="falso"))["statusCode"] == 401
    # otro cliente no ve ni la lista ni el detalle ni puede subir comprobante a la operación ajena
    assert cuerpo(ops.handler(evento("GET /operaciones", token=otro)))["total"] == 0
    p = {"id_operacion": op["id_operacion"]}
    assert ops.handler(evento("GET /operaciones/{id_operacion}", token=otro, params=p))["statusCode"] == 404
    assert subir(ops, otro, op["id_operacion"])["statusCode"] == 404


@pytest.mark.parametrize("cambio,status,codigo", [
    ({"content_type": "text/html"}, 422, "formato_no_permitido"),
    ({"content_type": "image/jpeg"}, 422, "archivo_invalido"),         # PNG disfrazado de JPG
    ({"contenido_base64": "%%%no-base64%%%"}, 400, "archivo_invalido"),
    ({"contenido_base64": base64.b64encode(b"MZ" + b"\0" * 100).decode()}, 422, "archivo_invalido"),
    ({"contenido_base64": base64.b64encode(b"%PDF" + b"0" * (5 * 1024 * 1024)).decode(), "content_type": "application/pdf"}, 413, "archivo_grande"),
])
def test_validacion_del_comprobante(cli, cot, ops, cambio, status, codigo):
    tk = sesion(cli)
    op = cuerpo(crear(ops, tk, hacer_cotizacion(cot)))
    r = subir(ops, tk, op["id_operacion"], **cambio)
    assert r["statusCode"] == status and cuerpo(r)["codigo"] == codigo


def test_nombre_de_archivo_peligroso_se_sanea(cli, cot, ops):
    tk = sesion(cli)
    op = cuerpo(crear(ops, tk, hacer_cotizacion(cot)))
    r = cuerpo(subir(ops, tk, op["id_operacion"], nombre_archivo="../../etc/pass wd?.png"))
    assert "/" not in r["comprobante_nombre"] and " " not in r["comprobante_nombre"]
    assert r["ruta_comprobante"].startswith(f"s3://nexo-test-comprobantes/comprobantes/{r['id_cliente']}/{r['id_operacion']}/")


def test_backoffice_avanza_estados_con_reglas(cli, cot, ops):
    tk = sesion(cli)
    op = cuerpo(crear(ops, tk, hacer_cotizacion(cot))); i = op["id_operacion"]; subir(ops, tk, i)
    p = {"id_operacion": i}

    def patch(estado, clave="clave-admin-pruebas", **extra):
        return ops.handler(evento("PATCH /operaciones/{id_operacion}/estado", {"estado": estado, **extra},
                                  params=p, headers={"x-admin-key": clave} if clave else {}))

    assert patch("En proceso", clave="incorrecta")["statusCode"] == 403
    assert patch("En proceso", clave=None)["statusCode"] == 403
    assert patch("Procesada")["statusCode"] == 409           # no se puede saltar "En proceso"
    assert cuerpo(patch("En proceso"))["estado"] == "En proceso"
    assert cuerpo(patch("Procesada"))["estado"] == "Procesada"
    assert patch("Rechazada", motivo_rechazo="x")["statusCode"] == 409   # estado final
    det = cuerpo(ops.handler(evento("GET /operaciones/{id_operacion}", token=tk, params=p)))
    assert [h["estado"] for h in det["historial"]] == ["Pendiente de validación", "En proceso", "Procesada"]


def test_backoffice_respuesta_del_patch_incluye_url_del_comprobante(cli, cot, ops):
    tk = sesion(cli)
    op = cuerpo(crear(ops, tk, hacer_cotizacion(cot))); i = op["id_operacion"]; subir(ops, tk, i)
    h = {"x-admin-key": "clave-admin-pruebas"}; p = {"id_operacion": i}
    r = cuerpo(ops.handler(evento("PATCH /operaciones/{id_operacion}/estado", {"estado": "En proceso"}, params=p, headers=h)))
    assert r["comprobante_url"].startswith("https://") and "X-Amz-Signature" in r["comprobante_url"]


def test_rechazo_exige_motivo_y_se_muestra_al_cliente(cli, cot, ops):
    tk = sesion(cli)
    op = cuerpo(crear(ops, tk, hacer_cotizacion(cot))); i = op["id_operacion"]; subir(ops, tk, i)
    h = {"x-admin-key": "clave-admin-pruebas"}; p = {"id_operacion": i}
    assert ops.handler(evento("PATCH /operaciones/{id_operacion}/estado", {"estado": "Rechazada"}, params=p, headers=h))["statusCode"] == 400
    ops.handler(evento("PATCH /operaciones/{id_operacion}/estado", {"estado": "Rechazada", "motivo_rechazo": "Monto no coincide"}, params=p, headers=h))
    det = cuerpo(ops.handler(evento("GET /operaciones/{id_operacion}", token=tk, params=p)))
    assert det["estado"] == "Rechazada" and det["motivo_rechazo"] == "Monto no coincide"


def test_backoffice_lista_operaciones_de_todos_los_clientes(cli, cot, ops):
    tk = sesion(cli)
    otro = sesion(cli, "otro@correo.com", {**PERSONA, "correo": "otro@correo.com", "numero_documento": "70000001"})
    op1 = cuerpo(crear(ops, tk, hacer_cotizacion(cot))); subir(ops, tk, op1["id_operacion"])
    op2 = cuerpo(crear(ops, otro, hacer_cotizacion(cot)))  # sin comprobante: sigue en borrador, no debe listarse
    h = {"x-admin-key": "clave-admin-pruebas"}
    r = ops.handler(evento("GET /operaciones/admin", headers=h))
    assert r["statusCode"] == 200
    ids = [o["id_operacion"] for o in cuerpo(r)["operaciones"]]
    assert op1["id_operacion"] in ids and op2["id_operacion"] not in ids

    assert ops.handler(evento("GET /operaciones/admin"))["statusCode"] == 403
    assert ops.handler(evento("GET /operaciones/admin", headers={"x-admin-key": "incorrecta"}))["statusCode"] == 403


def test_backoffice_detalle_no_depende_del_dueno(cli, cot, ops):
    tk = sesion(cli)
    op = cuerpo(crear(ops, tk, hacer_cotizacion(cot))); subir(ops, tk, op["id_operacion"])
    h = {"x-admin-key": "clave-admin-pruebas"}
    p = {"id_operacion": op["id_operacion"]}
    r = ops.handler(evento("GET /operaciones/{id_operacion}/admin", headers=h, params=p))
    assert r["statusCode"] == 200 and cuerpo(r)["comprobante_url"].startswith("https://")

    assert ops.handler(evento("GET /operaciones/{id_operacion}/admin", params=p))["statusCode"] == 403
    faltante = {"id_operacion": "NX-NOEXISTE"}
    r404 = ops.handler(evento("GET /operaciones/{id_operacion}/admin", headers=h, params=faltante))
    assert r404["statusCode"] == 404


def test_backoffice_deshabilitado_si_no_hay_clave_configurada(cli, cot, ops, monkeypatch):
    monkeypatch.setenv("ADMIN_KEY", "")
    r = ops.handler(evento("PATCH /operaciones/{id_operacion}/estado", {"estado": "En proceso"},
                           params={"id_operacion": "NX-1"}, headers={"x-admin-key": ""}))
    assert r["statusCode"] == 403


def test_ruta_desconocida_devuelve_404(ops):
    assert ops.handler({"routeKey": "DELETE /operaciones"})["statusCode"] == 404


def test_error_inesperado_no_filtra_detalles(ops, monkeypatch):
    monkeypatch.setattr(ops, "_tabla", lambda: (_ for _ in ()).throw(RuntimeError("secreto interno")))
    tk = nc.jwt_crear({"sub": "CLI-X"}, "secreto-de-pruebas-0123456789")
    r = ops.handler(evento("GET /operaciones", token=tk))
    assert r["statusCode"] == 500 and "secreto" not in r["body"]

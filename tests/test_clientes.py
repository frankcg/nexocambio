import time

import boto3
import pytest

from conftest import EMPRESA, PERSONA, cuerpo, evento
import nexo_common as nc


def registrar(cli, datos):
    return cli.handler(evento("POST /registro", datos))


def test_registro_persona_y_login(cli):
    r = registrar(cli, PERSONA)
    assert r["statusCode"] == 201 and cuerpo(r)["id_cliente"].startswith("CLI-")
    l = cli.handler(evento("POST /login", {"correo": "LUCIA@correo.com", "password": "Clave1234"}))
    assert l["statusCode"] == 200
    b = cuerpo(l)
    assert b["cliente"]["nombre"] == "Lucía Ramírez Torres" and "password_hash" not in b["cliente"]
    claims = nc.jwt_validar(b["token"], "secreto-de-pruebas-0123456789")
    assert claims["sub"] == b["cliente"]["id_cliente"]


def test_la_contrasena_se_guarda_con_hash_nunca_en_texto_plano(cli):
    registrar(cli, PERSONA)
    for it in boto3.resource("dynamodb").Table("nexo-test-clientes").scan()["Items"]:
        assert "Clave1234" not in str(it)
        if "password_hash" in it:
            assert it["password_hash"].startswith("pbkdf2_sha256$")


def test_registro_empresa(cli):
    r = registrar(cli, EMPRESA)
    assert r["statusCode"] == 201
    l = cuerpo(cli.handler(evento("POST /login", {"correo": "finanzas@andina.pe", "password": "Empresa2026"})))
    assert l["cliente"]["tipo_cliente"] == "empresa" and l["cliente"]["representante"]["cargo"] == "Gerente general"


def test_correo_y_documento_duplicados(cli):
    registrar(cli, PERSONA)
    r = registrar(cli, {**PERSONA, "numero_documento": "11111111"})
    assert r["statusCode"] == 409 and cuerpo(r)["codigo"] == "correo_duplicado"
    r = registrar(cli, {**PERSONA, "correo": "otra@correo.com"})
    assert r["statusCode"] == 409 and cuerpo(r)["codigo"] == "documento_duplicado"
    # la transacción es atómica: no quedaron ítems huérfanos del intento fallido
    claves = {i["pk"] for i in boto3.resource("dynamodb").Table("nexo-test-clientes").scan()["Items"]}
    assert "EMAIL#otra@correo.com" not in claves and "DOC#DNI#11111111" not in claves


@pytest.mark.parametrize("cambio,codigo", [
    ({"tipo_cliente": "x"}, "tipo_cliente_invalido"),
    ({"correo": "no-es-correo"}, "correo_invalido"),
    ({"telefono": "12345"}, "telefono_invalido"),
    ({"password": "corta1"}, "password_debil"),
    ({"password": "sololetrasaqui"}, "password_debil"),
    ({"numero_documento": "123"}, "documento_invalido"),
    ({"fecha_nacimiento": "2015-01-01"}, "menor_de_edad"),
    ({"fecha_nacimiento": "10/05/1994"}, "fecha_invalida"),
])
def test_validaciones_de_registro(cli, cambio, codigo):
    r = registrar(cli, {**PERSONA, **cambio})
    assert r["statusCode"] in (400, 422) and cuerpo(r)["codigo"] == codigo


def test_login_no_revela_si_el_correo_existe(cli):
    registrar(cli, PERSONA)
    a = cli.handler(evento("POST /login", {"correo": "lucia@correo.com", "password": "mala"}))
    b = cli.handler(evento("POST /login", {"correo": "nadie@correo.com", "password": "mala"}))
    assert a["statusCode"] == b["statusCode"] == 401 and a["body"] == b["body"]


def test_perfil_solo_del_propio_cliente(cli):
    registrar(cli, PERSONA); registrar(cli, EMPRESA)
    t1 = cuerpo(cli.handler(evento("POST /login", {"correo": "lucia@correo.com", "password": "Clave1234"})))
    t2 = cuerpo(cli.handler(evento("POST /login", {"correo": "finanzas@andina.pe", "password": "Empresa2026"})))
    ok = cli.handler(evento("GET /clientes/{id_cliente}", token=t1["token"], params={"id_cliente": t1["cliente"]["id_cliente"]}))
    assert ok["statusCode"] == 200 and cuerpo(ok)["correo"] == "lucia@correo.com"
    ajeno = cli.handler(evento("GET /clientes/{id_cliente}", token=t1["token"], params={"id_cliente": t2["cliente"]["id_cliente"]}))
    assert ajeno["statusCode"] == 403
    sin = cli.handler(evento("GET /clientes/{id_cliente}", params={"id_cliente": t1["cliente"]["id_cliente"]}))
    assert sin["statusCode"] == 401


def test_jwt_rechaza_firma_falsa_y_token_vencido():
    t = nc.jwt_crear({"sub": "CLI-X"}, "otro-secreto")
    with pytest.raises(nc.ApiError) as e:
        nc.jwt_validar(t, "secreto-de-pruebas-0123456789")
    assert e.value.status == 401
    vencido = nc.jwt_crear({"sub": "CLI-X"}, "s", ttl_seg=-10)
    with pytest.raises(nc.ApiError) as e:
        nc.jwt_validar(vencido, "s")
    assert e.value.codigo == "sesion_expirada"
    with pytest.raises(nc.ApiError):
        nc.jwt_validar("basura", "s")

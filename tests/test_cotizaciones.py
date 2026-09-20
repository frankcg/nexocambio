import time
from decimal import Decimal

import boto3
import pytest

from conftest import cuerpo, evento


def cotizar(cot, **kw):
    base = {"modalidad": "casa", "moneda_origen": "PEN", "moneda_destino": "USD", "monto_origen": 1000}
    return cot.handler(evento("POST /cotizar", {**base, **kw}))


def test_cotizacion_casa_de_cambio_calcula_tasa_y_monto(cot):
    r = cotizar(cot)
    c = cuerpo(r)
    assert r["statusCode"] == 201
    assert c["id_cotizacion"].startswith("COT-") and len(c["id_cotizacion"]) == 12
    # PEN→USD: (0.2954 / 1) * (1 - 0.45%)  →  0.29407..., monto 1000 → 294.07
    assert c["tasa"] == pytest.approx(0.2954 * (1 - 0.0045), rel=1e-6)
    assert c["monto_destino"] == pytest.approx(294.07, abs=0.01)
    assert c["tasa_preferencial"] is False
    assert c["fuente_tasas"] == "referencial"  # sin internet en las pruebas


def test_tasa_preferencial_desde_5000_usd(cot):
    c = cuerpo(cotizar(cot, moneda_origen="USD", moneda_destino="PEN", monto_origen=6000))
    assert c["tasa_preferencial"] is True
    assert c["tasa"] == pytest.approx((1 / 0.2954) * (1 - 0.0045 * 0.6), rel=1e-6)


def test_cripto_usa_spread_mayor_y_decimales_del_activo(cot):
    c = cuerpo(cotizar(cot, modalidad="cripto", moneda_origen="USD", moneda_destino="BTC", monto_origen=1000))
    assert c["monto_destino"] == pytest.approx(1000 / 98500 * (1 - 0.012), abs=1e-6)


def test_vigencia_de_5_minutos_y_registro_en_dynamodb(cot):
    c = cuerpo(cotizar(cot))
    item = boto3.resource("dynamodb").Table("nexo-test-cotizaciones").get_item(Key={"id_cotizacion": c["id_cotizacion"]})["Item"]
    assert int(item["expira_epoch"]) - int(time.time()) in range(295, 301)
    assert item["ttl"] > item["expira_epoch"]  # TTL de limpieza automática


@pytest.mark.parametrize("cambio,codigo,status", [
    ({"modalidad": "otra"}, "modalidad_invalida", 400),
    ({"moneda_destino": "PEN"}, "monedas_iguales", 422),
    ({"moneda_destino": "BTC"}, "moneda_no_disponible", 422),   # BTC no existe en Casa de Cambio
    ({"monto_origen": 0}, "monto_invalido", 422),
    ({"monto_origen": "abc"}, "monto_invalido", 400),
    ({"monto_origen": 5}, "monto_minimo", 422),                  # < US$ 10
    ({"monto_origen": 9_000_000}, "monto_maximo", 422),
    ({"modalidad": "cripto", "moneda_destino": "USD"}, "sin_cripto", 422),
])
def test_validaciones(cot, cambio, codigo, status):
    r = cotizar(cot, **cambio)
    assert r["statusCode"] == status and cuerpo(r)["codigo"] == codigo


def test_campos_obligatorios_y_json_invalido(cot):
    assert cot.handler(evento("POST /cotizar", {"modalidad": "casa"}))["statusCode"] == 400
    e = evento("POST /cotizar"); e["body"] = "{no es json"
    assert cot.handler(e)["statusCode"] == 400


def test_obtener_cotizacion_interna(cot):
    c = cuerpo(cotizar(cot))
    r = cot.handler({"accion": "obtener", "id_cotizacion": c["id_cotizacion"]})
    assert r["ok"] and r["cotizacion"]["segundos_restantes"] > 290
    assert cot.handler({"accion": "obtener", "id_cotizacion": "COT-NOEXISTE"})["ok"] is False


def test_tasas_en_vivo_se_guardan_y_se_reutilizan(cot, monkeypatch):
    monkeypatch.setenv("USAR_TASAS_EN_VIVO", "true")
    llamadas = []
    vivas = {"USD": Decimal(1), "PEN": Decimal("0.30"), "EUR": Decimal("1.10"), "USDT": Decimal(1),
             "USDC": Decimal(1), "BTC": Decimal(100000), "ETH": Decimal(4000)}
    monkeypatch.setattr(cot, "consultar_tasas_en_vivo", lambda: llamadas.append(1) or vivas)
    c1 = cuerpo(cotizar(cot))
    c2 = cuerpo(cotizar(cot))
    assert c1["fuente_tasas"] == "en_vivo" and c2["fuente_tasas"] == "en_vivo"
    assert len(llamadas) == 1  # la segunda cotización usó la caché de DynamoDB
    assert c1["tasa"] == pytest.approx(0.30 * (1 - 0.0045), rel=1e-6)


def test_si_falla_la_fuente_externa_no_se_rompe_y_no_reintenta_cada_request(cot, monkeypatch):
    monkeypatch.setenv("USAR_TASAS_EN_VIVO", "true")
    llamadas = []
    monkeypatch.setattr(cot, "consultar_tasas_en_vivo", lambda: llamadas.append(1) or {})
    assert cotizar(cot)["statusCode"] == 201
    assert cotizar(cot)["statusCode"] == 201
    assert len(llamadas) == 1

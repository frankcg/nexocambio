"""
nexo_cuentas — cuentas bancarias de NexoCambio (FICTICIAS, solo para la demo académica).

Misma fuente que frontend/src/app/features/operar/cuentas-nexo.ts. La usan la verificación de
NexoGuard (¿el destino es una cuenta de NexoCambio?) y la conciliación con el banco simulado.
"""
import re

# moneda -> banco -> (número de cuenta, CCI)
CUENTAS = {
    "PEN": {"BCP": ("193-2458710-0-39", "002-193-002458710039-14"),
            "Interbank": ("200-3001845527", "003-200-003001845527-38"),
            "BBVA": ("0011-0174-0100073152", "011-174-000100073152-86"),
            "Scotiabank": ("000-4127785", "009-170-000004127785-52")},
    "USD": {"BCP": ("193-2458711-1-47", "002-193-002458711147-17"),
            "Interbank": ("200-3001845534", "003-200-003001845534-31"),
            "BBVA": ("0011-0174-0100073160", "011-174-000100073160-81"),
            "Scotiabank": ("000-4127793", "009-170-000004127793-56")},
    "EUR": {"BCP": ("193-2458712-2-55", "002-193-002458712255-10")},
}


def digitos(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


def numeros(moneda: str) -> list:
    """Todos los números de cuenta y CCI (solo dígitos) de NexoCambio en esa moneda."""
    return [digitos(x) for par in CUENTAS.get(moneda, {}).values() for x in par]


def cuentas(moneda: str) -> list:
    """Solo los números de cuenta (sin CCI), que es como el banco identifica la cuenta."""
    return [digitos(c) for c, _ in CUENTAS.get(moneda, {}).values()]


def cuenta_de(valor: str, moneda: str):
    """Número de cuenta de NexoCambio al que corresponde una cuenta o CCI (también parcial, p. ej. '0039-14')."""
    v = digitos(valor)
    if len(v) < 2:
        return None
    for c, cci in CUENTAS.get(moneda, {}).values():
        if digitos(c).endswith(v) or digitos(cci).endswith(v):
            return digitos(c)
    return None

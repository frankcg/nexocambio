export const MONEDAS_CASA = ['PEN', 'USD', 'EUR'] as const;
export type MonedaCasa = (typeof MONEDAS_CASA)[number];

export const MONEDAS_CRIPTO = ['PEN', 'USD', 'USDT', 'USDC', 'BTC', 'ETH'] as const;
export type MonedaCripto = (typeof MONEDAS_CRIPTO)[number];

export type Moneda = MonedaCasa | MonedaCripto;

export const CRIPTOACTIVOS = ['USDT', 'USDC', 'BTC', 'ETH'] as const;
export type CriptoActivo = (typeof CRIPTOACTIVOS)[number];

export const BANCOS = ['BCP', 'Interbank', 'BBVA', 'Scotiabank', 'BanBif', 'Banco Pichincha'] as const;
export type Banco = (typeof BANCOS)[number];

export const TIPOS_CUENTA = ['Ahorros', 'Corriente'] as const;
export type TipoCuenta = (typeof TIPOS_CUENTA)[number];

export const REDES_POR_CRIPTO: Record<CriptoActivo, readonly string[]> = {
  USDT: ['TRON (TRC20)', 'Ethereum (ERC20)'],
  USDC: ['Ethereum (ERC20)', 'Solana'],
  BTC: ['Bitcoin'],
  ETH: ['Ethereum (ERC20)'],
};

export const DECIMALES_POR_MONEDA: Record<Moneda, number> = {
  PEN: 2,
  USD: 2,
  EUR: 2,
  USDT: 2,
  USDC: 2,
  BTC: 6,
  ETH: 5,
};

export function esCripto(moneda: Moneda): moneda is CriptoActivo {
  return (CRIPTOACTIVOS as readonly string[]).includes(moneda);
}

export const TIPOS_DOCUMENTO_PERSONA = ['DNI', 'CE', 'Pasaporte'] as const;
export type TipoDocumentoPersona = (typeof TIPOS_DOCUMENTO_PERSONA)[number];

export const OCUPACIONES = ['Dependiente', 'Independiente', 'Empresario', 'Estudiante', 'Jubilado', 'Otro'] as const;
export type Ocupacion = (typeof OCUPACIONES)[number];

export const ACTIVIDADES = ['Comercio', 'Servicios', 'Manufactura', 'Tecnología', 'Construcción', 'Otro'] as const;
export type Actividad = (typeof ACTIVIDADES)[number];

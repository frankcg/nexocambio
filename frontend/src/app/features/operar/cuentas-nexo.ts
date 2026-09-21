import { Destino, Origen } from '../../core/models/operacion.model';

export const MONEDA_NOMBRE: Record<string, string> = { PEN: 'soles', USD: 'dólares', EUR: 'euros' };

/** Cuentas y wallets de NexoCambio — FICTICIAS, solo para el prototipo/demo académica. */
const CUENTAS_NEXO: Record<string, Record<string, [string, string, string]>> = {
  BCP: {
    PEN: ['Cta. Corriente', '193-2458710-0-39', '002-193-002458710039-14'],
    USD: ['Cta. Corriente', '193-2458711-1-47', '002-193-002458711147-17'],
    EUR: ['Cta. Corriente', '193-2458712-2-55', '002-193-002458712255-10'],
  },
  Interbank: {
    PEN: ['Cta. Corriente', '200-3001845527', '003-200-003001845527-38'],
    USD: ['Cta. Corriente', '200-3001845534', '003-200-003001845534-31'],
  },
  BBVA: {
    PEN: ['Cta. Corriente', '0011-0174-0100073152', '011-174-000100073152-86'],
    USD: ['Cta. Corriente', '0011-0174-0100073160', '011-174-000100073160-81'],
  },
  Scotiabank: {
    PEN: ['Cta. Corriente', '000-4127785', '009-170-000004127785-52'],
    USD: ['Cta. Corriente', '000-4127793', '009-170-000004127793-56'],
  },
};

const WALLETS_NEXO: Record<string, string> = {
  'TRON (TRC20)': 'TNxDemoC4mb1oU7k9QeR2sWp6YhL3vB8aZ',
  'Ethereum (ERC20)': '0x4e5843616d62696f44656d6f0000000000A1f3',
  Solana: 'NxDemo7h2Kq9bVw4sP1eYt6RuC3mZ8gL5aF0jX',
  Bitcoin: 'bc1qnexodemo0cambio7x9p2k4w6s8u0y3r5t',
};

export type CuentaNexo =
  | { wallet: true; red: string; direccion: string }
  | { wallet: false; banco: string; tipo: string; numero: string; cci: string; interbancaria: boolean };

export function cuentaNexoPara(origen: Origen, monedaOrigen: string): CuentaNexo {
  if (origen.tipo === 'wallet') {
    return { wallet: true, red: origen.red, direccion: WALLETS_NEXO[origen.red] };
  }
  const misma = CUENTAS_NEXO[origen.banco]?.[monedaOrigen];
  if (misma) {
    return { wallet: false, banco: origen.banco, tipo: misma[0], numero: misma[1], cci: misma[2], interbancaria: false };
  }
  const bcp = CUENTAS_NEXO['BCP'][monedaOrigen];
  return { wallet: false, banco: 'BCP', tipo: bcp[0], numero: bcp[1], cci: bcp[2], interbancaria: true };
}

export function textoDestino(destino: Destino): string {
  return destino.tipo === 'banco' ? `${destino.banco} · ${destino.tipo_cuenta} · ${destino.numero}` : `${destino.red} · ${destino.direccion}`;
}

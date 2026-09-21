import { DECIMALES_POR_MONEDA, Moneda } from '../../core/models/catalogos.model';

export function formatearMonto(valor: number, moneda: string): string {
  const decimales = DECIMALES_POR_MONEDA[moneda as Moneda] ?? 2;
  return new Intl.NumberFormat('es-PE', { minimumFractionDigits: decimales, maximumFractionDigits: decimales }).format(valor);
}

export function formatearMoney(valor: number, moneda: string): string {
  return `${formatearMonto(valor, moneda)} ${moneda}`;
}

export function parsearMonto(texto: string): number {
  const valor = parseFloat(String(texto).replace(/,/g, ''));
  return Number.isFinite(valor) ? valor : NaN;
}

export function formatearFecha(iso: string): string {
  return new Intl.DateTimeFormat('es-PE', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(iso));
}

export function formatearHora(iso: string): string {
  return new Intl.DateTimeFormat('es-PE', { hour: '2-digit', minute: '2-digit' }).format(new Date(iso));
}

export function formatearFechaHora(iso: string): string {
  return `${formatearFecha(iso)}, ${formatearHora(iso)}`;
}

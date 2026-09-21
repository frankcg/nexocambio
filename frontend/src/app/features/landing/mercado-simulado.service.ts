import { Injectable, signal } from '@angular/core';
import { Modo } from '../../core/theme/theme.service';

/**
 * Simulación puramente decorativa de "mercado en vivo" para la landing (sparklines +
 * random walk), portada tal cual del prototipo. Una cotización ya emitida (backend real)
 * nunca depende de estos valores — solo alimenta las vistas de la landing.
 */
const MID_USD_INICIAL: Record<string, number> = { USD: 1, PEN: 1 / 3.385, EUR: 1.085, USDT: 1.0, USDC: 1.0, BTC: 98500, ETH: 3450 };
const VOL: Record<string, number> = { USD: 0, PEN: 0.00045, EUR: 0.0006, BTC: 0.0035, ETH: 0.0045, USDT: 0.00006, USDC: 0.00005 };
const HIST_N = 72;
export const SPREAD: Record<Modo, number> = { casa: 0.0045, cripto: 0.012 };
export const BANK_SPREAD = 0.025;
export const PREF_USD = 5000;

export interface ComparacionBanco {
  nexo: number;
  banco: number;
  ahorroPEN: number;
  tcNexo: number;
  tcBanco: number;
}

const MK_PAIRS: Record<Modo, [string, string, string][]> = {
  casa: [
    ['USD', 'PEN', 'Dólar estadounidense'],
    ['EUR', 'PEN', 'Euro'],
    ['EUR', 'USD', 'Euro / dólar'],
  ],
  cripto: [
    ['USDT', 'PEN', 'Tether'],
    ['USDC', 'PEN', 'USD Coin'],
    ['BTC', 'USD', 'Bitcoin'],
    ['ETH', 'USD', 'Ether'],
  ],
};

const COIN: Record<string, string> = { USD: '#1F7A4D', EUR: '#2C4FA3', USDT: '#26A17B', USDC: '#2775CA', BTC: '#E8870E', ETH: '#5B72D9' };

export interface FilaMercado {
  monedaA: string;
  monedaB: string;
  nombre: string;
  color: string;
  compra: string;
  venta: string;
  cambioTexto: string;
  subiendo: boolean;
  serie: number[];
}

export interface DatosBoard {
  par: string;
  compra: string;
  venta: string;
  cambioTexto: string;
  subiendo: boolean;
  serie: number[];
}

function nf(valor: number, decimales: number): string {
  return new Intl.NumberFormat('es-PE', { minimumFractionDigits: decimales, maximumFractionDigits: decimales }).format(valor);
}

function decimalesPar(v: number): number {
  return v >= 1000 ? 0 : v >= 10 ? 2 : v >= 2 ? 3 : 4;
}

function variacion(inicial: number, actual: number): { subiendo: boolean; texto: string } {
  const p = (actual / inicial - 1) * 100;
  return { subiendo: p >= 0, texto: `${p >= 0 ? '+' : '−'}${Math.abs(p).toFixed(2)}%` };
}

@Injectable()
export class MercadoSimuladoService {
  private readonly midUsd: Record<string, number> = { ...MID_USD_INICIAL };
  private readonly baseMid: Record<string, number> = { ...MID_USD_INICIAL };
  private readonly hist: Record<string, number[]> = {};

  private readonly _tick = signal(0);
  private readonly _ultimoTickEn = signal(Date.now());
  readonly ultimoTickEn = this._ultimoTickEn.asReadonly();

  private intervalo: ReturnType<typeof setInterval> | null = null;

  constructor() {
    let semilla = 11;
    const rnd = () => (semilla = (semilla * 16807) % 2147483647) / 2147483647;
    for (const moneda in MID_USD_INICIAL) {
      const arr = [MID_USD_INICIAL[moneda]];
      for (let i = 1; i < HIST_N; i++) {
        arr.unshift(arr[0] * (1 + (rnd() - 0.5) * 3.2 * VOL[moneda]));
      }
      this.hist[moneda] = arr;
    }
  }

  iniciar(): void {
    if (this.intervalo) return;
    this.intervalo = setInterval(() => this.paso(), 4000);
  }

  detener(): void {
    if (this.intervalo) clearInterval(this.intervalo);
    this.intervalo = null;
  }

  private paso(): void {
    if (document.hidden) return;
    for (const moneda in this.midUsd) {
      if (!VOL[moneda]) continue;
      let v = this.midUsd[moneda] * (1 + (Math.random() - 0.5) * 2 * VOL[moneda]);
      v += (this.baseMid[moneda] - v) * 0.03;
      this.midUsd[moneda] = v;
      this.hist[moneda].push(v);
      this.hist[moneda].shift();
    }
    this._ultimoTickEn.set(Date.now());
    this._tick.update((t) => t + 1);
  }

  private serie(a: string, b: string): number[] {
    return this.hist[a].map((v, i) => v / this.hist[b][i]);
  }

  filasDe(tab: Modo): FilaMercado[] {
    this._tick();
    const spread = SPREAD[tab];
    return MK_PAIRS[tab].map(([a, b, nombre]) => {
      const serie = this.serie(a, b);
      const mid = serie.at(-1)!;
      const dec = decimalesPar(mid);
      const { subiendo, texto } = variacion(serie[0], mid);
      return {
        monedaA: a,
        monedaB: b,
        nombre,
        color: COIN[a] ?? '#666',
        compra: nf(mid * (1 - spread), dec),
        venta: nf(mid * (1 + spread), dec),
        cambioTexto: texto,
        subiendo,
        serie: serie.slice(-40),
      };
    });
  }

  boardDe(modo: Modo): DatosBoard {
    this._tick();
    const [a, b] = modo === 'cripto' ? ['USDT', 'PEN'] : ['USD', 'PEN'];
    const serie = this.serie(a, b);
    const mid = serie.at(-1)!;
    const spread = SPREAD[modo];
    const { subiendo, texto } = variacion(serie[0], mid);
    return {
      par: `${a} / ${b}`,
      compra: nf(mid * (1 - spread), 3),
      venta: nf(mid * (1 + spread), 3),
      cambioTexto: texto,
      subiendo,
      serie,
    };
  }

  private readonly _parPendiente = signal<{ modo: Modo; origen: string; destino: string } | null>(null);
  readonly parPendiente = this._parPendiente.asReadonly();

  pedirPar(modo: Modo, origen: string, destino: string): void {
    this._parPendiente.set({ modo, origen, destino });
  }

  consumirParPendiente(): void {
    this._parPendiente.set(null);
  }

  tasaMid(moneda: string): number {
    this._tick();
    return this.midUsd[moneda];
  }

  calcularComparacion(pen: number): ComparacionBanco {
    this._tick();
    const mid = this.midUsd['PEN'];
    const usdMid = pen * mid;
    const nexoRate = mid * (1 - SPREAD.casa * (usdMid >= PREF_USD ? 0.6 : 1));
    const bankRate = mid * (1 - BANK_SPREAD);
    const nexo = pen * nexoRate;
    const banco = pen * bankRate;
    return { nexo, banco, ahorroPEN: (nexo - banco) / mid, tcNexo: 1 / nexoRate, tcBanco: 1 / bankRate };
  }

  /** Ahorro estimado en PEN frente a un banco tradicional (BANK_SPREAD), solo referencial. */
  ahorroFrenteABanco(montoOrigen: number, origen: string, destino: string, montoDestinoReal: number): number {
    const bank = montoOrigen * (this.midUsd[origen] / this.midUsd[destino]) * (1 - BANK_SPREAD);
    return (montoDestinoReal - bank) * (this.midUsd[destino] / this.midUsd['PEN']);
  }

  itemsTicker(): { par: string; sub: string; cambioTexto: string; subiendo: boolean }[] {
    this._tick();
    return [...MK_PAIRS.casa, ...MK_PAIRS.cripto].map(([a, b]) => {
      const modo: Modo = MK_PAIRS.casa.some((p) => p[0] === a) ? 'casa' : 'cripto';
      const serie = this.serie(a, b);
      const mid = serie.at(-1)!;
      const dec = decimalesPar(mid);
      const spread = SPREAD[modo];
      const { subiendo, texto } = variacion(serie[0], mid);
      return {
        par: `${a}/${b}`,
        sub: `${nf(mid * (1 - spread), dec)} · ${nf(mid * (1 + spread), dec)}`,
        cambioTexto: texto,
        subiendo,
      };
    });
  }
}

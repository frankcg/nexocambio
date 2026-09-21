import { Modo } from '../../core/theme/theme.service';

export interface ConfigModo {
  from: string[];
  to: string[];
  def: [string, string];
  monto: number;
  eyebrow: string;
  titulo: string;
  lead: string;
}

export const MODOS_QUOTER: Record<Modo, ConfigModo> = {
  casa: {
    from: ['PEN', 'USD', 'EUR'],
    to: ['USD', 'PEN', 'EUR'],
    def: ['PEN', 'USD'],
    monto: 1000,
    eyebrow: 'Casa de cambio digital',
    titulo: 'Cambia soles y dólares <em>sin salir de casa</em>.',
    lead: 'Cotiza al instante, transfiere desde tu banco y sigue el estado de tu operación en línea. Casa de Cambio y Cripto en una sola plataforma.',
  },
  cripto: {
    from: ['PEN', 'USD', 'USDT', 'USDC', 'BTC', 'ETH'],
    to: ['USDT', 'USDC', 'BTC', 'ETH', 'PEN', 'USD'],
    def: ['PEN', 'USDT'],
    monto: 1000,
    eyebrow: 'Cripto sin complicaciones',
    titulo: 'Compra y vende cripto <em>en soles</em>.',
    lead: 'USDT, USDC, BTC y ETH con la misma experiencia de siempre: cotiza, transfiere y adjunta tu comprobante.',
  },
};

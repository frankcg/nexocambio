import { Moneda } from './catalogos.model';

export type Modalidad = 'casa' | 'cripto';

export interface CrearCotizacionRequest {
  modalidad: Modalidad;
  moneda_origen: Moneda;
  moneda_destino: Moneda;
  monto_origen: number;
}

export interface Cotizacion {
  id_cotizacion: string;
  modalidad: Modalidad;
  moneda_origen: Moneda;
  moneda_destino: Moneda;
  monto_origen: number;
  tasa: number;
  tasa_preferencial: boolean;
  monto_destino: number;
  fuente_tasas: 'en_vivo' | 'cache' | 'referencial';
  fecha_cotizacion: string;
  fecha_expiracion: string;
}

import { Banco, TipoCuenta } from './catalogos.model';
import { Modalidad } from './cotizacion.model';
import { Moneda } from './catalogos.model';

export interface OrigenBanco {
  tipo: 'banco';
  banco: Banco;
}

export interface OrigenWallet {
  tipo: 'wallet';
  red: string;
}

export type Origen = OrigenBanco | OrigenWallet;

export interface DestinoBanco extends OrigenBanco {
  tipo_cuenta: TipoCuenta;
  numero: string;
  titular: string;
}

export interface DestinoWallet extends OrigenWallet {
  direccion: string;
}

export type Destino = DestinoBanco | DestinoWallet;

export interface CrearOperacionRequest {
  id_cotizacion: string;
  origen: Origen;
  destino: Destino;
}

export type EstadoOperacion =
  | 'Pendiente de comprobante'
  | 'Pendiente de validación'
  | 'En proceso'
  | 'Procesada'
  | 'Rechazada';

export interface HitoHistorial {
  estado: EstadoOperacion;
  fecha: string;
  motivo_rechazo?: string;
}

export interface Operacion {
  id_operacion: string;
  id_cliente: string;
  id_cotizacion: string;
  modalidad: Modalidad;
  moneda_origen: Moneda;
  moneda_destino: Moneda;
  monto_origen: number;
  monto_destino: number;
  tasa: number;
  tasa_preferencial: boolean;
  estado: EstadoOperacion;
  fecha_operacion: string;
  historial: HitoHistorial[];
  origen: Origen;
  destino: Destino;
  motivo_rechazo?: string;
  ruta_comprobante?: string;
  comprobante_nombre?: string;
  comprobante_tipo?: string;
  comprobante_tamano?: number;
  comprobante_url?: string;
  numero_transferencia?: string;
}

export interface ListarOperacionesResponse {
  operaciones: Operacion[];
  total: number;
}

export type ContentTypeComprobante = 'image/jpeg' | 'image/png' | 'image/webp' | 'application/pdf';

export interface SubirComprobanteRequest {
  nombre_archivo: string;
  content_type: ContentTypeComprobante;
  contenido_base64: string;
  numero_transferencia?: string;
}

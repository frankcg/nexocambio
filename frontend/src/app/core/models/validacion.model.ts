import { EstadoOperacion } from './operacion.model';

/** NexoGuard: estado de la validación automática de un comprobante. */
export type EstadoValidacion = 'en_curso' | 'en_revision' | 'finalizada';
export type Semaforo = 'verde' | 'amarillo' | 'rojo';
export type DecididoPor = 'agente' | 'operador';

/** Vista del cliente: GET /validaciones/{id} (sin semáforo ni justificación interna). */
export interface ValidacionCliente {
  id_operacion: string;
  estado: EstadoValidacion;
  fecha_inicio: string;
  fecha_fin?: string | null;
  estado_final?: EstadoOperacion | null;
  decidido_por?: DecididoPor | null;
  motivo?: string | null;
}

export interface ReglaVerificacion {
  regla: string;
  resultado: 'cumple' | 'no_cumple' | 'no_concluyente';
  gravedad: 'rechazo' | 'revision' | 'informativa';
  detalle: string;
}

export interface Extraccion {
  es_comprobante: boolean | null;
  legible: boolean;
  banco_origen: string | null;
  monto: number | null;
  moneda: string | null;
  fecha: string | null;
  hora: string | null;
  numero_operacion: string | null;
  destinatario: string | null;
  cuenta_destino: string | null;
  banco_destino: string | null;
  confianza: number;
  observaciones: string;
  modelo?: string | null;
}

/** Vista del back-office: GET /validaciones/{id}/admin y GET /validaciones/admin. */
export interface Validacion {
  id_operacion: string;
  fecha_inicio: string;
  id_cliente: string;
  estado: EstadoValidacion;
  monto_origen: number;
  moneda_origen: string;
  comprobante?: string;
  extraccion?: Extraccion;
  verificaciones?: ReglaVerificacion[];
  semaforo?: Semaforo;
  justificacion?: string;
  ruta?: 'aprobar' | 'revision' | 'rechazar';
  alerta_cumplimiento?: boolean;
  monto_usd?: number;
  motivo_sugerido?: string | null;
  numero_operacion?: string;
  fecha_revision?: string;
  fecha_fin?: string;
  estado_final?: EstadoOperacion;
  decision?: { decision: 'aprobar' | 'rechazar'; decidido_por: DecididoPor; motivo: string | null; fecha: string };
  /** Conciliación con la API bancaria (simulada): ¿llegó el depósito a una cuenta de NexoCambio? */
  conciliacion?: {
    coincidencia: 'total' | 'parcial' | 'ninguna' | 'error' | 'no_aplica' | 'no_consultado' | null;
    detalle?: string | null;
    intento?: number | null;
    deposito?: { monto: number; moneda: string; numero_operacion: string; fecha: string; banco_origen: string; ordenante: string } | null;
  };
  modelos?: { vision: string | null; texto: string | null };
}

export interface ListarValidacionesResponse {
  validaciones: Validacion[];
  total: number;
}

export interface ValidacionesOperacionResponse {
  id_operacion: string;
  validaciones: Validacion[];
  total: number;
}

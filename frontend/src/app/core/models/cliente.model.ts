import { Actividad, Ocupacion, TipoDocumentoPersona } from './catalogos.model';

export interface RegistroPersonaRequest {
  tipo_cliente: 'persona';
  nombres: string;
  apellidos: string;
  tipo_documento: TipoDocumentoPersona;
  numero_documento: string;
  fecha_nacimiento: string;
  telefono: string;
  ocupacion?: Ocupacion;
  pep: boolean;
  correo: string;
  password: string;
}

export interface RegistroEmpresaRequest {
  tipo_cliente: 'empresa';
  razon_social: string;
  tipo_documento: 'RUC';
  numero_documento: string;
  actividad?: Actividad;
  telefono: string;
  correo: string;
  password: string;
  representante: {
    nombre: string;
    tipo_documento: TipoDocumentoPersona;
    numero_documento: string;
    cargo: string;
  };
}

export type RegistroRequest = RegistroPersonaRequest | RegistroEmpresaRequest;

export interface RegistroResponse {
  id_cliente: string;
  mensaje: string;
}

export interface LoginRequest {
  correo: string;
  password: string;
}

export interface Cliente {
  id_cliente: string;
  tipo_cliente: 'persona' | 'empresa';
  nombre: string;
  correo: string;
  telefono: string;
  [clave: string]: unknown;
}

export interface LoginResponse {
  token: string;
  expira_en: number;
  cliente: Cliente;
}

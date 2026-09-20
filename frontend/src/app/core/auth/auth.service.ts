import { Injectable, computed, signal } from '@angular/core';
import { Cliente } from '../models/cliente.model';

const CLAVE_SESION = 'nexo_sesion';

interface SesionGuardada {
  token: string;
  cliente: Cliente;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly _token = signal<string | null>(null);
  private readonly _cliente = signal<Cliente | null>(null);

  readonly token = this._token.asReadonly();
  readonly cliente = this._cliente.asReadonly();
  readonly autenticado = computed(() => this._token() !== null);

  constructor() {
    const guardada = this.leerSesion();
    if (guardada) {
      this._token.set(guardada.token);
      this._cliente.set(guardada.cliente);
    }
  }

  login(token: string, cliente: Cliente): void {
    this._token.set(token);
    this._cliente.set(cliente);
    try {
      sessionStorage.setItem(CLAVE_SESION, JSON.stringify({ token, cliente }));
    } catch {
      /* sessionStorage no disponible: la sesión sigue en memoria para esta pestaña */
    }
  }

  logout(): void {
    this._token.set(null);
    this._cliente.set(null);
    try {
      sessionStorage.removeItem(CLAVE_SESION);
    } catch {
      /* sessionStorage no disponible */
    }
  }

  private leerSesion(): SesionGuardada | null {
    try {
      const bruto = sessionStorage.getItem(CLAVE_SESION);
      return bruto ? (JSON.parse(bruto) as SesionGuardada) : null;
    } catch {
      return null;
    }
  }
}

import { Injectable, computed, signal } from '@angular/core';

const CLAVE_ALMACENAMIENTO = 'nexo_admin_key';

@Injectable({ providedIn: 'root' })
export class AdminAuthService {
  private readonly _clave = signal<string | null>(this.leerGuardada());
  readonly clave = this._clave.asReadonly();
  readonly autenticado = computed(() => this._clave() !== null);

  iniciarSesion(clave: string): void {
    this._clave.set(clave);
    try {
      sessionStorage.setItem(CLAVE_ALMACENAMIENTO, clave);
    } catch {
      /* sessionStorage no disponible: la sesión de admin sigue en memoria para esta pestaña */
    }
  }

  salir(): void {
    this._clave.set(null);
    try {
      sessionStorage.removeItem(CLAVE_ALMACENAMIENTO);
    } catch {
      /* sessionStorage no disponible */
    }
  }

  private leerGuardada(): string | null {
    try {
      return sessionStorage.getItem(CLAVE_ALMACENAMIENTO);
    } catch {
      return null;
    }
  }
}

import { Injectable, signal } from '@angular/core';
import { Cotizacion } from '../models/cotizacion.model';

const CLAVE_DRAFT = 'nexo_borrador';

@Injectable({ providedIn: 'root' })
export class DraftCotizacionService {
  private readonly _cotizacion = signal<Cotizacion | null>(this.leerGuardado());
  readonly cotizacion = this._cotizacion.asReadonly();

  guardar(cotizacion: Cotizacion): void {
    this._cotizacion.set(cotizacion);
    try {
      sessionStorage.setItem(CLAVE_DRAFT, JSON.stringify(cotizacion));
    } catch {
      /* sessionStorage no disponible: el draft sigue en memoria para esta pestaña */
    }
  }

  limpiar(): void {
    this._cotizacion.set(null);
    try {
      sessionStorage.removeItem(CLAVE_DRAFT);
    } catch {
      /* sessionStorage no disponible */
    }
  }

  private leerGuardado(): Cotizacion | null {
    try {
      const bruto = sessionStorage.getItem(CLAVE_DRAFT);
      return bruto ? (JSON.parse(bruto) as Cotizacion) : null;
    } catch {
      return null;
    }
  }
}

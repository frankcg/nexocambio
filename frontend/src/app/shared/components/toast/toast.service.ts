import { Injectable, signal } from '@angular/core';

export interface ToastMensaje {
  titulo: string;
  cuerpo: string;
}

const DURACION_MS = 4200;

@Injectable({ providedIn: 'root' })
export class ToastService {
  private readonly _actual = signal<ToastMensaje | null>(null);
  readonly actual = this._actual.asReadonly();
  private temporizador: ReturnType<typeof setTimeout> | null = null;

  mostrar(titulo: string, cuerpo: string): void {
    this._actual.set({ titulo, cuerpo });
    if (this.temporizador) {
      clearTimeout(this.temporizador);
    }
    this.temporizador = setTimeout(() => this._actual.set(null), DURACION_MS);
  }
}

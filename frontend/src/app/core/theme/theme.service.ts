import { Injectable, signal } from '@angular/core';

export type Modo = 'casa' | 'cripto';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly _modo = signal<Modo>('casa');
  readonly modo = this._modo.asReadonly();

  establecer(modo: Modo): void {
    this._modo.set(modo);
    document.documentElement.dataset['mode'] = modo;
  }
}

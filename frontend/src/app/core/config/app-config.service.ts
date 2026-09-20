import { Injectable, signal } from '@angular/core';

interface ConfigRuntime {
  apiBaseUrl: string;
}

@Injectable({ providedIn: 'root' })
export class AppConfigService {
  private readonly _apiBaseUrl = signal<string | null>(null);
  readonly apiBaseUrl = this._apiBaseUrl.asReadonly();

  async cargar(): Promise<void> {
    const respuesta = await fetch('config.json');
    if (!respuesta.ok) {
      throw new Error(`No se pudo cargar config.json (${respuesta.status})`);
    }
    const config: ConfigRuntime = await respuesta.json();
    this._apiBaseUrl.set(config.apiBaseUrl.replace(/\/$/, ''));
  }
}

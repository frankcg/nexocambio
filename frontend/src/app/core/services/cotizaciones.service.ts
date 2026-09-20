import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { AppConfigService } from '../config/app-config.service';
import { Cotizacion, CrearCotizacionRequest } from '../models/cotizacion.model';

@Injectable({ providedIn: 'root' })
export class CotizacionesService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(AppConfigService);

  cotizar(datos: CrearCotizacionRequest): Observable<Cotizacion> {
    return this.http.post<Cotizacion>(`${this.config.apiBaseUrl()}/cotizar`, datos);
  }
}

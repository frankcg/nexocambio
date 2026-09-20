import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { AppConfigService } from '../config/app-config.service';
import {
  CrearOperacionRequest,
  ListarOperacionesResponse,
  Operacion,
  SubirComprobanteRequest,
} from '../models/operacion.model';

@Injectable({ providedIn: 'root' })
export class OperacionesService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(AppConfigService);

  crear(datos: CrearOperacionRequest): Observable<Operacion> {
    return this.http.post<Operacion>(`${this.config.apiBaseUrl()}/operaciones`, datos);
  }

  subirComprobante(idOperacion: string, datos: SubirComprobanteRequest): Observable<Operacion> {
    return this.http.post<Operacion>(`${this.config.apiBaseUrl()}/operaciones/${idOperacion}/comprobante`, datos);
  }

  listar(): Observable<ListarOperacionesResponse> {
    return this.http.get<ListarOperacionesResponse>(`${this.config.apiBaseUrl()}/operaciones`);
  }

  obtener(idOperacion: string): Observable<Operacion> {
    return this.http.get<Operacion>(`${this.config.apiBaseUrl()}/operaciones/${idOperacion}`);
  }
}

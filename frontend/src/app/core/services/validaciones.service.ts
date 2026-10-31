import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { AppConfigService } from '../config/app-config.service';
import { AdminAuthService } from '../admin-auth/admin-auth.service';
import {
  EstadoValidacion,
  ListarValidacionesResponse,
  ValidacionCliente,
  ValidacionesOperacionResponse,
} from '../models/validacion.model';

/** API Validaciones (NexoGuard). El cliente usa su JWT (interceptor); el back-office, x-admin-key. */
@Injectable({ providedIn: 'root' })
export class ValidacionesService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(AppConfigService);
  private readonly adminAuth = inject(AdminAuthService);

  private cabecerasAdmin(): HttpHeaders {
    return new HttpHeaders({ 'x-admin-key': this.adminAuth.clave() ?? '' });
  }

  obtener(idOperacion: string): Observable<ValidacionCliente> {
    return this.http.get<ValidacionCliente>(`${this.config.apiBaseUrl()}/validaciones/${idOperacion}`);
  }

  listarAdmin(estado: EstadoValidacion = 'en_revision'): Observable<ListarValidacionesResponse> {
    return this.http.get<ListarValidacionesResponse>(`${this.config.apiBaseUrl()}/validaciones/admin`, {
      headers: this.cabecerasAdmin(),
      params: { estado },
    });
  }

  obtenerAdmin(idOperacion: string): Observable<ValidacionesOperacionResponse> {
    return this.http.get<ValidacionesOperacionResponse>(`${this.config.apiBaseUrl()}/validaciones/${idOperacion}/admin`, {
      headers: this.cabecerasAdmin(),
    });
  }

  decidir(idOperacion: string, decision: 'aprobar' | 'rechazar', motivo?: string): Observable<{ mensaje: string }> {
    const cuerpo: { decision: string; motivo?: string } = { decision };
    if (motivo) cuerpo.motivo = motivo;
    return this.http.post<{ mensaje: string }>(`${this.config.apiBaseUrl()}/validaciones/${idOperacion}/decision`, cuerpo, {
      headers: this.cabecerasAdmin(),
    });
  }
}

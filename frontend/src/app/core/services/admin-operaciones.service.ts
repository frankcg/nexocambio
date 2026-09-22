import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { AppConfigService } from '../config/app-config.service';
import { AdminAuthService } from '../admin-auth/admin-auth.service';
import { EstadoOperacion, ListarOperacionesResponse, Operacion } from '../models/operacion.model';

@Injectable({ providedIn: 'root' })
export class AdminOperacionesService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(AppConfigService);
  private readonly adminAuth = inject(AdminAuthService);

  private cabeceras(): HttpHeaders {
    return new HttpHeaders({ 'x-admin-key': this.adminAuth.clave() ?? '' });
  }

  listar(): Observable<ListarOperacionesResponse> {
    return this.http.get<ListarOperacionesResponse>(`${this.config.apiBaseUrl()}/operaciones/admin`, {
      headers: this.cabeceras(),
    });
  }

  obtener(idOperacion: string): Observable<Operacion> {
    return this.http.get<Operacion>(`${this.config.apiBaseUrl()}/operaciones/${idOperacion}/admin`, {
      headers: this.cabeceras(),
    });
  }

  cambiarEstado(idOperacion: string, estado: EstadoOperacion, motivoRechazo?: string): Observable<Operacion> {
    const cuerpo: { estado: EstadoOperacion; motivo_rechazo?: string } = { estado };
    if (motivoRechazo) cuerpo.motivo_rechazo = motivoRechazo;
    return this.http.patch<Operacion>(`${this.config.apiBaseUrl()}/operaciones/${idOperacion}/estado`, cuerpo, {
      headers: this.cabeceras(),
    });
  }
}

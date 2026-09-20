import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { AppConfigService } from '../config/app-config.service';
import { Cliente, LoginRequest, LoginResponse, RegistroRequest, RegistroResponse } from '../models/cliente.model';

@Injectable({ providedIn: 'root' })
export class ClientesService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(AppConfigService);

  registrar(datos: RegistroRequest): Observable<RegistroResponse> {
    return this.http.post<RegistroResponse>(`${this.config.apiBaseUrl()}/registro`, datos);
  }

  login(datos: LoginRequest): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.config.apiBaseUrl()}/login`, datos);
  }

  obtenerPerfil(idCliente: string): Observable<Cliente> {
    return this.http.get<Cliente>(`${this.config.apiBaseUrl()}/clientes/${idCliente}`);
  }
}

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { AdminLista } from './admin-lista';
import { AdminAuthService } from '../../../core/admin-auth/admin-auth.service';
import { ListarOperacionesResponse } from '../../../core/models/operacion.model';

const RESPUESTA: ListarOperacionesResponse = {
  total: 2,
  operaciones: [
    {
      id_operacion: 'NX-0002',
      id_cliente: 'CLI-1',
      id_cotizacion: 'COT-2',
      modalidad: 'casa',
      moneda_origen: 'PEN',
      moneda_destino: 'USD',
      monto_origen: 1000,
      monto_destino: 294,
      tasa: 0.294,
      tasa_preferencial: false,
      estado: 'Pendiente de validación',
      fecha_operacion: new Date().toISOString(),
      historial: [],
      origen: { tipo: 'banco', banco: 'BCP' },
      destino: { tipo: 'banco', banco: 'BCP', tipo_cuenta: 'Ahorros', numero: '123', titular: 'Ana' },
    },
    {
      id_operacion: 'NX-0001',
      id_cliente: 'CLI-2',
      id_cotizacion: 'COT-1',
      modalidad: 'casa',
      moneda_origen: 'PEN',
      moneda_destino: 'USD',
      monto_origen: 500,
      monto_destino: 147,
      tasa: 0.294,
      tasa_preferencial: false,
      estado: 'En proceso',
      fecha_operacion: new Date().toISOString(),
      historial: [],
      origen: { tipo: 'banco', banco: 'BCP' },
      destino: { tipo: 'banco', banco: 'BCP', tipo_cuenta: 'Ahorros', numero: '123', titular: 'Ana' },
    },
  ],
};

describe('AdminLista', () => {
  let component: AdminLista;
  let fixture: ComponentFixture<AdminLista>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    sessionStorage.clear();
    await TestBed.configureTestingModule({
      imports: [AdminLista],
      providers: [provideRouter([]), provideHttpClientTesting()],
    }).compileComponents();

    TestBed.inject(AdminAuthService).iniciarSesion('clave-admin-pruebas');
    fixture = TestBed.createComponent(AdminLista);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('adjunta x-admin-key y filtra por "Pendiente de validación" por defecto', () => {
    const solicitud = httpMock.expectOne((r) => r.url.endsWith('/operaciones/admin'));
    expect(solicitud.request.headers.get('x-admin-key')).toBe('clave-admin-pruebas');
    solicitud.flush(RESPUESTA);
    fixture.detectChanges();

    expect(component['filtradas']().length).toBe(1);
    expect(component['filtradas']()[0].id_operacion).toBe('NX-0002');
  });

  it('redirige a /admin/login si la clave es rechazada (403)', () => {
    const router = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigateByUrl');
    const adminAuth = TestBed.inject(AdminAuthService);

    httpMock.expectOne((r) => r.url.endsWith('/operaciones/admin')).flush(
      { mensaje: 'Acceso restringido al back-office.', codigo: 'prohibido' },
      { status: 403, statusText: 'Forbidden' }
    );
    fixture.detectChanges();

    expect(adminAuth.autenticado()).toBe(false);
    expect(navigateSpy).toHaveBeenCalledWith('/admin/login');
  });
});

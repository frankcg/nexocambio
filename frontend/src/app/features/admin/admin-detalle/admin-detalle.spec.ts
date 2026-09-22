import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { AdminDetalle } from './admin-detalle';
import { AdminAuthService } from '../../../core/admin-auth/admin-auth.service';
import { Operacion } from '../../../core/models/operacion.model';

const OPERACION: Operacion = {
  id_operacion: 'NX-0001',
  id_cliente: 'CLI-1',
  id_cotizacion: 'COT-1',
  modalidad: 'casa',
  moneda_origen: 'PEN',
  moneda_destino: 'USD',
  monto_origen: 1000,
  monto_destino: 294,
  tasa: 0.294,
  tasa_preferencial: false,
  estado: 'Pendiente de validación',
  fecha_operacion: new Date().toISOString(),
  historial: [{ estado: 'Pendiente de validación', fecha: new Date().toISOString() }],
  origen: { tipo: 'banco', banco: 'BCP' },
  destino: { tipo: 'banco', banco: 'BCP', tipo_cuenta: 'Ahorros', numero: '123', titular: 'Ana' },
};

describe('AdminDetalle', () => {
  let component: AdminDetalle;
  let fixture: ComponentFixture<AdminDetalle>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    sessionStorage.clear();
    await TestBed.configureTestingModule({
      imports: [AdminDetalle],
      providers: [
        provideRouter([]),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'NX-0001' }) } } },
      ],
    }).compileComponents();

    TestBed.inject(AdminAuthService).iniciarSesion('clave-admin-pruebas');
    fixture = TestBed.createComponent(AdminDetalle);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function cargar(estadoInicial: Operacion = OPERACION) {
    httpMock.expectOne((r) => r.url.endsWith('/operaciones/NX-0001/admin') && r.method === 'GET').flush(estadoInicial);
    fixture.detectChanges();
  }

  it('propone "En proceso" cuando está Pendiente de validación', () => {
    cargar();
    expect(component['siguienteAprobado']()).toBe('En proceso');
  });

  it('aprobar() envía PATCH con el siguiente estado', () => {
    cargar();
    component['aprobar']();
    const solicitud = httpMock.expectOne((r) => r.url.endsWith('/operaciones/NX-0001/estado') && r.method === 'PATCH');
    expect(solicitud.request.headers.get('x-admin-key')).toBe('clave-admin-pruebas');
    expect(solicitud.request.body).toEqual({ estado: 'En proceso' });
    solicitud.flush({ ...OPERACION, estado: 'En proceso' });
    fixture.detectChanges();
    expect(component['operacion']()?.estado).toBe('En proceso');
  });

  it('exige un motivo de al menos 3 caracteres para rechazar', () => {
    cargar();
    component['mostrarFormularioRechazo']();
    component['onCambioMotivo']('ok');
    component['confirmarRechazo']();
    expect(component['errorAccion']()).toContain('al menos 3 caracteres');
  });

  it('confirmarRechazo() envía el motivo junto con el estado', () => {
    cargar();
    component['mostrarFormularioRechazo']();
    component['onCambioMotivo']('El monto no coincide');
    component['confirmarRechazo']();
    const solicitud = httpMock.expectOne((r) => r.url.endsWith('/operaciones/NX-0001/estado') && r.method === 'PATCH');
    expect(solicitud.request.body).toEqual({ estado: 'Rechazada', motivo_rechazo: 'El monto no coincide' });
    solicitud.flush({ ...OPERACION, estado: 'Rechazada', motivo_rechazo: 'El monto no coincide' });
    fixture.detectChanges();
    expect(component['operacion']()?.estado).toBe('Rechazada');
  });

  it('no ofrece acciones cuando la operación ya está en un estado final', () => {
    cargar({ ...OPERACION, estado: 'Procesada' });
    expect(component['puedeAccionar']()).toBe(false);
  });
});

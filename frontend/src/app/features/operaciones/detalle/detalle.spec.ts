import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { Detalle } from './detalle';
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
  estado: 'En proceso',
  fecha_operacion: new Date().toISOString(),
  historial: [{ estado: 'Pendiente de validación', fecha: new Date().toISOString() }],
  origen: { tipo: 'banco', banco: 'BCP' },
  destino: { tipo: 'banco', banco: 'BCP', tipo_cuenta: 'Ahorros', numero: '123', titular: 'Ana' },
};

describe('Detalle', () => {
  let component: Detalle;
  let fixture: ComponentFixture<Detalle>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Detalle],
      providers: [
        provideRouter([]),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'NX-0001' }) } } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Detalle);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('muestra el detalle y marca los hitos de la línea de tiempo', () => {
    httpMock.expectOne((r) => r.url.endsWith('/operaciones/NX-0001') && r.method === 'GET').flush(OPERACION);
    fixture.detectChanges();

    expect(component['estaHecho']('Pendiente de validación')).toBe(true);
    expect(component['estaHecho']('En proceso')).toBe(true);
    expect(component['estaHecho']('Procesada')).toBe(false);
    expect(fixture.nativeElement.textContent).toContain('NX-0001');
  });
});

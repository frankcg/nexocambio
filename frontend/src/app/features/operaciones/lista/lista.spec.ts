import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { Lista } from './lista';
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
      id_cliente: 'CLI-1',
      id_cotizacion: 'COT-1',
      modalidad: 'casa',
      moneda_origen: 'PEN',
      moneda_destino: 'USD',
      monto_origen: 500,
      monto_destino: 147,
      tasa: 0.294,
      tasa_preferencial: false,
      estado: 'Rechazada',
      fecha_operacion: new Date().toISOString(),
      historial: [],
      origen: { tipo: 'banco', banco: 'BCP' },
      destino: { tipo: 'banco', banco: 'BCP', tipo_cuenta: 'Ahorros', numero: '123', titular: 'Ana' },
    },
  ],
};

describe('Lista', () => {
  let component: Lista;
  let fixture: ComponentFixture<Lista>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Lista],
      providers: [provideRouter([]), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(Lista);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('muestra el resumen y filtra por estado', () => {
    httpMock.expectOne((r) => r.url.endsWith('/operaciones') && r.method === 'GET').flush(RESPUESTA);
    fixture.detectChanges();

    expect(component['enCurso']()).toBe(1);
    expect(component['filtradas']().length).toBe(2);

    component['elegirFiltro']('Rechazada');
    fixture.detectChanges();
    expect(component['filtradas']().length).toBe(1);
    expect(component['filtradas']()[0].id_operacion).toBe('NX-0001');
  });

  it('muestra el estado vacío cuando no hay operaciones', () => {
    httpMock.expectOne((r) => r.url.endsWith('/operaciones') && r.method === 'GET').flush({ operaciones: [], total: 0 });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Todavía no tienes operaciones');
  });
});

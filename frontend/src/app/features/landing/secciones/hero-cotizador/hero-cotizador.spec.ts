import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { HeroCotizador } from './hero-cotizador';
import { MercadoSimuladoService } from '../../mercado-simulado.service';
import { Cotizacion } from '../../../../core/models/cotizacion.model';

describe('HeroCotizador', () => {
  let component: HeroCotizador;
  let fixture: ComponentFixture<HeroCotizador>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HeroCotizador],
      providers: [provideRouter([]), provideHttpClientTesting(), MercadoSimuladoService],
    }).compileComponents();

    fixture = TestBed.createComponent(HeroCotizador);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should create', () => {
    httpMock.expectOne((r) => r.url.endsWith('/cotizar'));
    expect(component).toBeTruthy();
  });

  it('muestra la tasa y habilita "Operar ahora" cuando la API responde', () => {
    const solicitud = httpMock.expectOne((r) => r.url.endsWith('/cotizar'));
    const respuesta: Cotizacion = {
      id_cotizacion: 'COT-TEST0001',
      modalidad: 'casa',
      moneda_origen: 'PEN',
      moneda_destino: 'USD',
      monto_origen: 1000,
      tasa: 0.294,
      tasa_preferencial: false,
      monto_destino: 294,
      fuente_tasas: 'en_vivo',
      fecha_cotizacion: new Date().toISOString(),
      fecha_expiracion: new Date(Date.now() + 300_000).toISOString(),
    };
    solicitud.flush(respuesta);
    fixture.detectChanges();

    const boton = fixture.nativeElement.querySelector('button.cta') as HTMLButtonElement;
    expect(boton.disabled).toBe(false);
    expect(boton.textContent).toContain('Operar ahora');
  });

  it('muestra un mensaje de error cuando ambas monedas son iguales', () => {
    httpMock.expectOne((r) => r.url.endsWith('/cotizar')).flush({
      id_cotizacion: 'COT-X',
      modalidad: 'casa',
      moneda_origen: 'PEN',
      moneda_destino: 'USD',
      monto_origen: 1000,
      tasa: 0.294,
      tasa_preferencial: false,
      monto_destino: 294,
      fuente_tasas: 'referencial',
      fecha_cotizacion: new Date().toISOString(),
      fecha_expiracion: new Date(Date.now() + 300_000).toISOString(),
    } as Cotizacion);
    fixture.detectChanges();

    component['cambiarMonedaDestino']('PEN');
    fixture.detectChanges();

    expect(component['errorMensaje']()).toBe('Elige monedas distintas para enviar y recibir.');
  });
});

import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { operarGuard } from './operar.guard';
import { DraftCotizacionService } from './draft-cotizacion.service';
import { Cotizacion } from '../models/cotizacion.model';

const COTIZACION: Cotizacion = {
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

describe('operarGuard', () => {
  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
  });

  it('permite entrar cuando hay una cotización en borrador', () => {
    TestBed.inject(DraftCotizacionService).guardar(COTIZACION);
    const resultado = TestBed.runInInjectionContext(() => operarGuard({} as never, { url: '/operar' } as never));
    expect(resultado).toBe(true);
  });

  it('redirige a / cuando no hay cotización en borrador', () => {
    const resultado = TestBed.runInInjectionContext(() => operarGuard({} as never, { url: '/operar' } as never));
    const router = TestBed.inject(Router);
    expect(resultado).toEqual(router.createUrlTree(['/']));
  });
});

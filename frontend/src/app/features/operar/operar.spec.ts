import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { Operar } from './operar';
import { AuthService } from '../../core/auth/auth.service';
import { DraftCotizacionService } from '../../core/draft/draft-cotizacion.service';
import { Cotizacion } from '../../core/models/cotizacion.model';
import { Cliente } from '../../core/models/cliente.model';
import { Operacion } from '../../core/models/operacion.model';

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

const CLIENTE: Cliente = {
  id_cliente: 'CLI-TEST01',
  tipo_cliente: 'persona',
  nombre: 'Ana Torres',
  correo: 'ana@nexocambio.pe',
  telefono: '987654321',
};

describe('Operar', () => {
  let component: Operar;
  let fixture: ComponentFixture<Operar>;
  let httpMock: HttpTestingController;
  let draft: DraftCotizacionService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Operar],
      providers: [provideRouter([]), provideHttpClientTesting()],
    }).compileComponents();

    draft = TestBed.inject(DraftCotizacionService);
    draft.guardar(COTIZACION);
    TestBed.inject(AuthService).login('token-test', CLIENTE);

    fixture = TestBed.createComponent(Operar);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => httpMock.verify());

  it('muestra el paso 1 con el resumen de la cotización', () => {
    expect(fixture.nativeElement.textContent).toContain('Confirma tu cotización');
    expect(fixture.nativeElement.textContent).toContain('1,000.00 PEN');
  });

  it('completa el flujo cotizar -> confirmar -> transferir -> comprobante -> resultado', async () => {
    component['form'].controls.banco_origen.setValue('BCP');
    component['form'].controls.banco_destino.setValue('BCP');
    component['form'].controls.numero_cuenta.setValue('1932458710039');
    component['confirmarYContinuar']();
    fixture.detectChanges();
    expect(component['paso']()).toBe(2);

    component['irAComprobante']();
    fixture.detectChanges();
    expect(component['paso']()).toBe(3);

    const archivo = new File(['contenido'], 'voucher.jpg', { type: 'image/jpeg' });
    component['procesarArchivo'](archivo);
    fixture.detectChanges();
    expect(component['archivoPendiente']()).toBe(archivo);

    component['confirmarOperacion']();

    // FileReader.readAsDataURL termina de forma asíncrona; esperamos su resolución real.
    await new Promise((r) => setTimeout(r, 50));
    fixture.detectChanges();

    const solicitudCrear = httpMock.expectOne((r) => r.url.endsWith('/operaciones') && r.method === 'POST');
    const operacionCreada: Operacion = {
      id_operacion: 'NX-TEST0001',
      id_cliente: CLIENTE.id_cliente,
      id_cotizacion: COTIZACION.id_cotizacion,
      modalidad: 'casa',
      moneda_origen: 'PEN',
      moneda_destino: 'USD',
      monto_origen: 1000,
      monto_destino: 294,
      tasa: 0.294,
      tasa_preferencial: false,
      estado: 'Pendiente de comprobante',
      fecha_operacion: new Date().toISOString(),
      historial: [],
      origen: { tipo: 'banco', banco: 'BCP' },
      destino: { tipo: 'banco', banco: 'BCP', tipo_cuenta: 'Ahorros', numero: '1932458710039', titular: 'Ana Torres' },
    };
    solicitudCrear.flush(operacionCreada);

    const solicitudComprobante = httpMock.expectOne((r) => r.url.endsWith('/operaciones/NX-TEST0001/comprobante') && r.method === 'POST');
    solicitudComprobante.flush({ ...operacionCreada, estado: 'Pendiente de validación' });

    fixture.detectChanges();
    expect(component['paso']()).toBe(4);
    expect(component['resultado']()?.estado).toBe('Pendiente de validación');
  });
});

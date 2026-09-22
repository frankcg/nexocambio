import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { map, of, tap } from 'rxjs';
import { AuthService } from '../../core/auth/auth.service';
import { DraftCotizacionService } from '../../core/draft/draft-cotizacion.service';
import { CotizacionesService } from '../../core/services/cotizaciones.service';
import { OperacionesService } from '../../core/services/operaciones.service';
import { ToastService } from '../../shared/components/toast/toast.service';
import { CampoError } from '../../shared/components/campo-error/campo-error';
import { Stepper } from '../../shared/components/stepper/stepper';
import { BotonCopiar } from '../../shared/components/boton-copiar/boton-copiar';
import { BANCOS, Banco, CriptoActivo, MONEDAS_CASA, REDES_POR_CRIPTO, TIPOS_CUENTA, TipoCuenta } from '../../core/models/catalogos.model';
import { Cotizacion } from '../../core/models/cotizacion.model';
import { ContentTypeComprobante, Destino, EstadoOperacion, Origen } from '../../core/models/operacion.model';
import { ErrorApi } from '../../core/models/error-api.model';
import { cuentaBancariaValidator, walletValidator } from '../../shared/validators/nexo-validators';
import { formatearMonto, formatearMoney } from '../../shared/utils/moneda';
import { formatearMmss, segundosRestantesHasta } from '../../shared/utils/tiempo';
import { MONEDA_NOMBRE, cuentaNexoPara, textoDestino } from './cuentas-nexo';

const FIAT = MONEDAS_CASA as readonly string[];
const PASOS = ['Datos de la operación', 'Transferencia', 'Comprobante'];
const MENSAJE_ERROR_RED = 'No pudimos conectar con el servidor. Revisa tu conexión e inténtalo otra vez.';
const TIPOS_ARCHIVO_PERMITIDOS = ['image/jpeg', 'image/png', 'application/pdf'];
const MAX_COMPROBANTE_BYTES = 4 * 1048576;

@Component({
  selector: 'app-operar',
  imports: [ReactiveFormsModule, RouterLink, CampoError, Stepper, BotonCopiar],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './operar.html',
})
export class Operar {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly draft = inject(DraftCotizacionService);
  private readonly cotizaciones = inject(CotizacionesService);
  private readonly operaciones = inject(OperacionesService);
  private readonly toast = inject(ToastService);

  protected readonly PASOS = PASOS;
  protected readonly TIPOS_CUENTA = TIPOS_CUENTA;
  protected readonly BANCOS = BANCOS;

  // Copia local de la cotización, independiente del draft compartido: operarGuard garantiza que
  // exista una al entrar, pero el draft se limpia al terminar (paso 4) y esa pantalla final sigue
  // necesitando estos datos, así que no puede depender reactivamente del servicio.
  protected readonly x = signal<Cotizacion>(this.draft.cotizacion()!);

  protected readonly paso = signal(1);
  protected readonly origen = signal<Origen | null>(null);
  protected readonly destino = signal<Destino | null>(null);
  protected readonly idOperacion = signal<string | null>(null);
  protected readonly resultado = signal<{ id_operacion: string; estado: EstadoOperacion } | null>(null);

  protected readonly nro = signal('');
  protected readonly archivoPendiente = signal<File | null>(null);
  protected readonly previewUrl = signal<string | null>(null);
  protected readonly errorArchivo = signal('');
  protected readonly arrastrando = signal(false);

  protected readonly enviando = signal(false);
  protected readonly errorGeneral = signal('');
  protected readonly segundosRestantes = signal(0);
  protected readonly vencida = computed(() => this.segundosRestantes() === 0);

  protected readonly origenEsFiat = computed(() => FIAT.includes(this.x().moneda_origen));
  protected readonly destinoEsFiat = computed(() => FIAT.includes(this.x().moneda_destino));
  protected readonly redesOrigen = computed(() => (this.origenEsFiat() ? [] : REDES_POR_CRIPTO[this.x().moneda_origen as CriptoActivo]));
  protected readonly redesDestino = computed(() => (this.destinoEsFiat() ? [] : REDES_POR_CRIPTO[this.x().moneda_destino as CriptoActivo]));
  protected readonly nombreMonedaOrigen = computed(() => MONEDA_NOMBRE[this.x().moneda_origen] ?? '');
  protected readonly nombreMonedaDestino = computed(() => MONEDA_NOMBRE[this.x().moneda_destino] ?? '');

  protected readonly cuentaNexo = computed(() => {
    const o = this.origen();
    return o ? cuentaNexoPara(o, this.x().moneda_origen) : null;
  });
  protected readonly textoDestinoElegido = computed(() => {
    const d = this.destino();
    return d ? textoDestino(d) : '';
  });

  protected origenTexto(): string {
    const o = this.origen();
    if (!o) return '';
    return o.tipo === 'banco' ? o.banco : o.red;
  }

  protected origenBancoTexto(): string {
    const o = this.origen();
    return o?.tipo === 'banco' ? o.banco : '';
  }

  protected readonly form = this.fb.nonNullable.group({
    banco_origen: this.fb.nonNullable.control<Banco>(BANCOS[0]),
    red_origen: [''],
    banco_destino: this.fb.nonNullable.control<Banco>(BANCOS[0]),
    tipo_cuenta: this.fb.nonNullable.control<TipoCuenta>('Ahorros'),
    numero_cuenta: ['', [Validators.required, cuentaBancariaValidator()]],
    titular: [{ value: '', disabled: true }],
    red_destino: [''],
    wallet: ['', [Validators.required, walletValidator()]],
  });

  constructor() {
    this.actualizarSegundos();
    const intervalo = setInterval(() => this.actualizarSegundos(), 1000);
    inject(DestroyRef).onDestroy(() => intervalo && clearInterval(intervalo));

    effect(() => {
      const x = this.x();
      if (!FIAT.includes(x.moneda_origen)) {
        this.form.controls.red_origen.setValue(REDES_POR_CRIPTO[x.moneda_origen as CriptoActivo][0]);
      }
      if (!FIAT.includes(x.moneda_destino)) {
        this.form.controls.red_destino.setValue(REDES_POR_CRIPTO[x.moneda_destino as CriptoActivo][0]);
      }
    });

    effect(() => {
      const cliente = this.auth.cliente();
      if (cliente) this.form.controls.titular.setValue(cliente.nombre);
    });
  }

  protected textoMonto(): string {
    const x = this.x();
    return formatearMoney(x.monto_origen, x.moneda_origen);
  }

  protected textoMontoDestino(): string {
    const x = this.x();
    return formatearMoney(x.monto_destino, x.moneda_destino);
  }

  protected textoTasa(): string {
    const x = this.x();
    const dec = x.tasa >= 100 ? 2 : 4;
    return `1 ${x.moneda_origen} = ${new Intl.NumberFormat('es-PE', { minimumFractionDigits: dec, maximumFractionDigits: dec }).format(x.tasa)} ${x.moneda_destino}`;
  }

  protected etiquetaTasa(): string {
    const x = this.x();
    if (x.modalidad === 'cripto') return FIAT.includes(x.moneda_origen) ? 'Precio de compra' : 'Precio de venta';
    if (x.moneda_origen === 'PEN') return 'Tipo de cambio venta';
    if (x.moneda_destino === 'PEN') return 'Tipo de cambio compra';
    return 'Tipo de cambio';
  }

  protected textoTemporizador(): string {
    return this.vencida() ? 'La tasa venció. Actualízala para continuar.' : `Tasa válida por ${formatearMmss(this.segundosRestantes())}`;
  }

  protected proporcionBarra(): number {
    return this.segundosRestantes() / 300;
  }

  private actualizarSegundos(): void {
    this.segundosRestantes.set(segundosRestantesHasta(this.x().fecha_expiracion));
  }

  protected confirmarYContinuar(): void {
    if (this.vencida()) {
      this.actualizarCotizacion();
      return;
    }

    const campos = this.origenEsFiat() ? (['banco_origen'] as const) : (['red_origen'] as const);
    const camposDestino = this.destinoEsFiat() ? (['banco_destino', 'tipo_cuenta', 'numero_cuenta'] as const) : (['red_destino', 'wallet'] as const);
    let hayInvalido = false;
    for (const nombre of [...campos, ...camposDestino]) {
      const control = this.form.controls[nombre];
      control.markAsTouched();
      if (control.invalid) hayInvalido = true;
    }
    if (hayInvalido) return;

    const d = this.form.getRawValue();
    const origen: Origen = this.origenEsFiat() ? { tipo: 'banco', banco: d.banco_origen } : { tipo: 'wallet', red: d.red_origen };
    const destino: Destino = this.destinoEsFiat()
      ? { tipo: 'banco', banco: d.banco_destino, tipo_cuenta: d.tipo_cuenta, numero: d.numero_cuenta.replace(/[\s-]/g, ''), titular: d.titular }
      : { tipo: 'wallet', red: d.red_destino, direccion: d.wallet };
    this.origen.set(origen);
    this.destino.set(destino);
    this.paso.set(2);
  }

  private actualizarCotizacion(): void {
    const x = this.x();
    this.enviando.set(true);
    this.cotizaciones.cotizar({ modalidad: x.modalidad, moneda_origen: x.moneda_origen, moneda_destino: x.moneda_destino, monto_origen: x.monto_origen }).subscribe({
      next: (nueva) => {
        this.x.set(nueva);
        this.draft.guardar(nueva);
        this.enviando.set(false);
        this.actualizarSegundos();
        this.toast.mostrar('Tasa actualizada', `Ahora recibes ${formatearMoney(nueva.monto_destino, nueva.moneda_destino)}.`);
      },
      error: () => {
        this.enviando.set(false);
        this.toast.mostrar('No se pudo actualizar', 'Inténtalo nuevamente.');
      },
    });
  }

  protected volverAPaso1(): void {
    this.paso.set(1);
  }

  protected irAComprobante(): void {
    this.paso.set(3);
  }

  protected onFileChange(evento: Event): void {
    const input = evento.target as HTMLInputElement;
    const archivo = input.files?.[0];
    if (archivo) this.procesarArchivo(archivo);
  }

  protected onDrop(evento: DragEvent): void {
    evento.preventDefault();
    this.arrastrando.set(false);
    const archivo = evento.dataTransfer?.files?.[0];
    if (archivo) this.procesarArchivo(archivo);
  }

  protected onDragOver(evento: DragEvent): void {
    evento.preventDefault();
    this.arrastrando.set(true);
  }

  protected onDragLeave(evento: DragEvent): void {
    evento.preventDefault();
    this.arrastrando.set(false);
  }

  private procesarArchivo(archivo: File): void {
    this.errorArchivo.set('');
    if (!TIPOS_ARCHIVO_PERMITIDOS.includes(archivo.type)) {
      this.errorArchivo.set('Formato no permitido. Sube una imagen JPG o PNG, o un PDF.');
      return;
    }
    if (archivo.size > MAX_COMPROBANTE_BYTES) {
      this.errorArchivo.set(`El archivo pesa ${(archivo.size / 1048576).toFixed(1)} MB. El máximo es 4 MB.`);
      return;
    }
    this.archivoPendiente.set(archivo);
    this.previewUrl.set(archivo.type.startsWith('image/') ? URL.createObjectURL(archivo) : null);
  }

  protected quitarArchivo(): void {
    this.archivoPendiente.set(null);
    this.previewUrl.set(null);
  }

  protected onCambioNro(valor: string): void {
    this.nro.set(valor);
  }

  protected confirmarOperacion(): void {
    const archivo = this.archivoPendiente();
    if (!archivo) return;

    this.errorGeneral.set('');
    this.enviando.set(true);
    const lector = new FileReader();
    lector.onload = () => {
      const base64 = String(lector.result).split(',')[1];
      this.enviarComprobante(base64, archivo);
    };
    lector.onerror = () => {
      this.enviando.set(false);
      this.errorGeneral.set('No pudimos leer el archivo. Inténtalo nuevamente.');
    };
    lector.readAsDataURL(archivo);
  }

  private enviarComprobante(base64: string, archivo: File): void {
    const origen = this.origen();
    const destino = this.destino();
    if (!origen || !destino) return;

    const idExistente = this.idOperacion();
    const idOperacion$ = idExistente
      ? of(idExistente)
      : this.operaciones.crear({ id_cotizacion: this.x().id_cotizacion, origen, destino }).pipe(
          tap((op) => this.idOperacion.set(op.id_operacion)),
          map((op) => op.id_operacion)
        );

    idOperacion$.subscribe({
      next: (idOperacion) => {
        this.operaciones
          .subirComprobante(idOperacion, {
            nombre_archivo: archivo.name,
            content_type: archivo.type as ContentTypeComprobante,
            contenido_base64: base64,
            numero_transferencia: this.nro().trim() || undefined,
          })
          .subscribe({
            next: (operacion) => {
              this.enviando.set(false);
              this.resultado.set({ id_operacion: idOperacion, estado: operacion.estado });
              this.draft.limpiar();
              this.paso.set(4);
            },
            error: (error: HttpErrorResponse) => {
              this.enviando.set(false);
              this.errorGeneral.set((error.error as ErrorApi | undefined)?.mensaje ?? MENSAJE_ERROR_RED);
            },
          });
      },
      error: (error: HttpErrorResponse) => {
        this.enviando.set(false);
        this.errorGeneral.set((error.error as ErrorApi | undefined)?.mensaje ?? MENSAJE_ERROR_RED);
      },
    });
  }

  protected formatearMontoOrigenExacto(): string {
    const x = this.x();
    return formatearMonto(x.monto_origen, x.moneda_origen);
  }
}

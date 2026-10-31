import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { OperacionesService } from '../../../core/services/operaciones.service';
import { EstadoOperacion, Operacion } from '../../../core/models/operacion.model';
import { ErrorApi } from '../../../core/models/error-api.model';
import { formatearFechaHora, formatearMoney } from '../../../shared/utils/moneda';
import { MONEDAS_CASA } from '../../../core/models/catalogos.model';
import { EstadoNexoguard } from '../../../shared/components/estado-nexoguard/estado-nexoguard';

const FIAT = MONEDAS_CASA as readonly string[];
const INTERVALO_ACTUALIZACION_MS = 10000;

const DESCRIPCION_ESTADO: Record<string, string> = {
  'Pendiente de validación': 'Recibimos tu comprobante.',
  'En proceso': 'Transferencia validada. Estamos enviando tu cambio.',
  Procesada: 'Enviamos el dinero a tu cuenta.',
};

@Component({
  selector: 'app-detalle',
  imports: [RouterLink, EstadoNexoguard],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './detalle.html',
})
export class Detalle {
  private readonly operacionesSvc = inject(OperacionesService);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly operacion = signal<Operacion | null>(null);

  protected readonly rechazada = computed(() => this.operacion()?.estado === 'Rechazada');

  protected readonly flujo = computed<EstadoOperacion[]>(() =>
    this.rechazada() ? ['Pendiente de validación', 'Rechazada'] : ['Pendiente de validación', 'En proceso', 'Procesada']
  );

  private readonly id = this.ruta.snapshot.paramMap.get('id')!;
  private temporizador: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    inject(DestroyRef).onDestroy(() => this.temporizador && clearTimeout(this.temporizador));
    this.cargar();
  }

  /** NexoGuard terminó: recarga la operación para mostrar su nuevo estado e historial. */
  protected onValidacionTerminada(): void {
    this.cargar();
  }

  protected actorHito(estado: EstadoOperacion): string | null {
    const hito = this.operacion()?.historial.find((h) => h.estado === estado);
    if (hito?.actor === 'agente') return 'Validado automáticamente por NexoGuard';
    if (hito?.actor === 'operador' && hito.origen === 'nexoguard') return 'Revisado por un especialista';
    return null;
  }

  private cargar(): void {
    if (this.temporizador) clearTimeout(this.temporizador);
    const primeraCarga = this.operacion() === null;
    this.operacionesSvc.obtener(this.id).subscribe({
      next: (o) => {
        const previa = this.operacion();
        // La URL firmada del comprobante cambia en cada consulta: se conserva para que la imagen no parpadee
        if (previa?.ruta_comprobante && previa.ruta_comprobante === o.ruta_comprobante) o = { ...o, comprobante_url: previa.comprobante_url };
        this.operacion.set(o);
        this.cargando.set(false);
        this.programarActualizacion(o.estado);
      },
      error: (e: HttpErrorResponse) => {
        if (!primeraCarga) {
          this.programarActualizacion(this.operacion()!.estado); // falla puntual de red: se reintenta en silencio
          return;
        }
        this.error.set((e.error as ErrorApi | undefined)?.mensaje ?? 'No encontramos esta operación en tu cuenta.');
        this.cargando.set(false);
      },
    });
  }

  /** Mientras la operación no termine, se vuelve a consultar sola (p. ej. cuando el back-office la marca Procesada). */
  private programarActualizacion(estado: EstadoOperacion): void {
    if (estado === 'Procesada' || estado === 'Rechazada') return;
    this.temporizador = setTimeout(() => this.cargar(), INTERVALO_ACTUALIZACION_MS);
  }

  protected textoTasa(): string {
    const o = this.operacion();
    if (!o) return '—';
    const dec = o.tasa >= 100 ? 2 : 4;
    return `1 ${o.moneda_origen} = ${new Intl.NumberFormat('es-PE', { minimumFractionDigits: dec, maximumFractionDigits: dec }).format(o.tasa)} ${o.moneda_destino}`;
  }

  protected etiquetaTasa(): string {
    const o = this.operacion();
    if (!o) return 'Tipo de cambio';
    if (o.modalidad === 'cripto') return FIAT.includes(o.moneda_origen) ? 'Precio de compra' : 'Precio de venta';
    if (o.moneda_origen === 'PEN') return 'Tipo de cambio venta';
    if (o.moneda_destino === 'PEN') return 'Tipo de cambio compra';
    return 'Tipo de cambio';
  }

  protected origenTexto(): string {
    const o = this.operacion()?.origen;
    if (!o) return '—';
    return o.tipo === 'wallet' ? o.red : o.banco;
  }

  protected etiquetaOrigen(): string {
    return this.operacion()?.origen.tipo === 'wallet' ? 'Red de envío' : 'Banco de origen';
  }

  protected fechaHito(estado: EstadoOperacion): string | null {
    const o = this.operacion();
    if (!o) return null;
    const hito = o.historial.find((h) => h.estado === estado);
    return hito ? hito.fecha : null;
  }

  protected estaHecho(estado: EstadoOperacion): boolean {
    return this.fechaHito(estado) !== null || this.operacion()?.estado === estado;
  }

  protected descripcionEstado(estado: EstadoOperacion): string {
    const o = this.operacion();
    if (estado === 'Rechazada') return o?.motivo_rechazo || 'No pudimos validar la transferencia.';
    return DESCRIPCION_ESTADO[estado] ?? '';
  }

  protected fechaHora(iso: string): string {
    return formatearFechaHora(iso);
  }

  protected monto(valor: number, moneda: string): string {
    return formatearMoney(valor, moneda);
  }

  protected claseEstado(estado: EstadoOperacion): string {
    if (estado === 'Pendiente de validación') return 's-pend';
    if (estado === 'En proceso') return 's-proc';
    if (estado === 'Procesada') return 's-ok';
    return 's-bad';
  }
}

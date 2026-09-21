import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { OperacionesService } from '../../../core/services/operaciones.service';
import { EstadoOperacion, Operacion } from '../../../core/models/operacion.model';
import { ErrorApi } from '../../../core/models/error-api.model';
import { formatearFechaHora, formatearMoney } from '../../../shared/utils/moneda';
import { MONEDAS_CASA } from '../../../core/models/catalogos.model';

const FIAT = MONEDAS_CASA as readonly string[];

const DESCRIPCION_ESTADO: Record<string, string> = {
  'Pendiente de validación': 'Recibimos tu comprobante.',
  'En proceso': 'Transferencia validada. Estamos enviando tu cambio.',
  Procesada: 'Enviamos el dinero a tu cuenta.',
};

@Component({
  selector: 'app-detalle',
  imports: [RouterLink],
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

  constructor() {
    const id = this.ruta.snapshot.paramMap.get('id')!;
    this.operacionesSvc.obtener(id).subscribe({
      next: (o) => {
        this.operacion.set(o);
        this.cargando.set(false);
      },
      error: (e: HttpErrorResponse) => {
        this.error.set((e.error as ErrorApi | undefined)?.mensaje ?? 'No encontramos esta operación en tu cuenta.');
        this.cargando.set(false);
      },
    });
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

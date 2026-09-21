import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { OperacionesService } from '../../../core/services/operaciones.service';
import { EstadoOperacion, Operacion } from '../../../core/models/operacion.model';
import { ErrorApi } from '../../../core/models/error-api.model';
import { formatearFecha, formatearMoney } from '../../../shared/utils/moneda';

type Filtro = 'Todas' | EstadoOperacion;

const ESTADOS: EstadoOperacion[] = ['Pendiente de validación', 'En proceso', 'Procesada', 'Rechazada'];

/** Tasas referenciales solo para el resumen "Total operado" (aproximado, sin fines contables). */
const TASA_REF_USD: Record<string, number> = { PEN: 1 / 3.385, USD: 1, EUR: 1.085, USDT: 1, USDC: 1, BTC: 98500, ETH: 3450 };

@Component({
  selector: 'app-lista',
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './lista.html',
})
export class Lista {
  private readonly operacionesSvc = inject(OperacionesService);

  protected readonly ESTADOS = ESTADOS;
  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly operaciones = signal<Operacion[]>([]);
  protected readonly filtro = signal<Filtro>('Todas');

  protected readonly conteos = computed(() => {
    const ops = this.operaciones();
    return Object.fromEntries(ESTADOS.map((e) => [e, ops.filter((o) => o.estado === e).length])) as Record<EstadoOperacion, number>;
  });

  protected readonly enCurso = computed(() => this.conteos()['Pendiente de validación'] + this.conteos()['En proceso']);

  protected readonly totalOperadoTexto = computed(() => {
    const total = this.operaciones()
      .filter((o) => o.estado !== 'Rechazada')
      .reduce((t, o) => t + o.monto_origen * (TASA_REF_USD[o.moneda_origen] ?? 1), 0);
    return `US$ ${new Intl.NumberFormat('es-PE', { maximumFractionDigits: 0 }).format(total)}`;
  });

  protected readonly ultimaOperacion = computed(() => this.operaciones()[0] ?? null);

  protected readonly filtradas = computed(() => {
    const f = this.filtro();
    return f === 'Todas' ? this.operaciones() : this.operaciones().filter((o) => o.estado === f);
  });

  constructor() {
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.operacionesSvc.listar().subscribe({
      next: (r) => {
        this.operaciones.set(r.operaciones);
        this.cargando.set(false);
      },
      error: (e: HttpErrorResponse) => {
        this.error.set((e.error as ErrorApi | undefined)?.mensaje ?? 'No pudimos conectar con el servidor. Revisa tu conexión e inténtalo otra vez.');
        this.cargando.set(false);
      },
    });
  }

  protected elegirFiltro(f: Filtro): void {
    this.filtro.set(f);
  }

  protected fecha(iso: string): string {
    return formatearFecha(iso);
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

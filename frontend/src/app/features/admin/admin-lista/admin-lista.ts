import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';
import { AdminOperacionesService } from '../../../core/services/admin-operaciones.service';
import { AdminAuthService } from '../../../core/admin-auth/admin-auth.service';
import { EstadoOperacion, Operacion } from '../../../core/models/operacion.model';
import { ErrorApi } from '../../../core/models/error-api.model';
import { formatearFechaHora, formatearMoney } from '../../../shared/utils/moneda';

type Filtro = 'Todas' | EstadoOperacion;

const ESTADOS: EstadoOperacion[] = ['Pendiente de validación', 'En proceso', 'Procesada', 'Rechazada'];

@Component({
  selector: 'app-admin-lista',
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './admin-lista.html',
})
export class AdminLista {
  private readonly admin = inject(AdminOperacionesService);
  private readonly adminAuth = inject(AdminAuthService);
  private readonly router = inject(Router);

  protected readonly ESTADOS = ESTADOS;
  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly operaciones = signal<Operacion[]>([]);
  protected readonly filtro = signal<Filtro>('Pendiente de validación');

  protected readonly conteos = computed(() => {
    const ops = this.operaciones();
    return Object.fromEntries(ESTADOS.map((e) => [e, ops.filter((o) => o.estado === e).length])) as Record<EstadoOperacion, number>;
  });

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
    this.admin.listar().subscribe({
      next: (r) => {
        this.operaciones.set(r.operaciones);
        this.cargando.set(false);
      },
      error: (e: HttpErrorResponse) => {
        if (e.status === 403) {
          this.adminAuth.salir();
          this.router.navigateByUrl('/admin/login');
          return;
        }
        this.error.set((e.error as ErrorApi | undefined)?.mensaje ?? 'No pudimos conectar con el servidor. Revisa tu conexión e inténtalo otra vez.');
        this.cargando.set(false);
      },
    });
  }

  protected elegirFiltro(f: Filtro): void {
    this.filtro.set(f);
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

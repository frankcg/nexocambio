import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';
import { AdminOperacionesService } from '../../../core/services/admin-operaciones.service';
import { AdminAuthService } from '../../../core/admin-auth/admin-auth.service';
import { EstadoOperacion, Operacion } from '../../../core/models/operacion.model';
import { ErrorApi } from '../../../core/models/error-api.model';
import { ValidacionesService } from '../../../core/services/validaciones.service';
import { Validacion } from '../../../core/models/validacion.model';
import { formatearFechaHora, formatearMoney } from '../../../shared/utils/moneda';

type Filtro = 'Todas' | 'NexoGuard' | EstadoOperacion;

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
  private readonly validacionesSvc = inject(ValidacionesService);

  protected readonly ESTADOS = ESTADOS;
  /** NexoGuard: operaciones que el workflow envió a revisión humana (cola de la API Validaciones). */
  private readonly colaNexoguard = signal<Validacion[]>([]);
  /** Solo las que siguen pendientes: si un operador resolvió la operación con el PATCH manual, sale de la cola. */
  protected readonly enRevision = computed(() => {
    const pendientes = new Set(this.operaciones().filter((o) => o.estado === 'Pendiente de validación').map((o) => o.id_operacion));
    return this.colaNexoguard().filter((v) => pendientes.has(v.id_operacion));
  });
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
    this.validacionesSvc.listarAdmin('en_revision').subscribe({
      next: (r) => this.colaNexoguard.set(r.validaciones),
      error: () => this.colaNexoguard.set([]), // si NexoGuard no responde, la cola manual sigue disponible
    });
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

  protected readonly reiniciando = signal(false);

  /** Entorno académico: deja la demo lista para repetirse con los mismos comprobantes. */
  protected reiniciarDemo(): void {
    const mensaje = 'Se borrarán TODAS las operaciones, validaciones y depósitos de prueba (los clientes se conservan). ¿Continuar?';
    if (!window.confirm(mensaje)) return;
    this.reiniciando.set(true);
    this.validacionesSvc.reiniciarDemo(true).subscribe({
      next: () => {
        this.reiniciando.set(false);
        this.cargar();
      },
      error: (e: HttpErrorResponse) => {
        this.reiniciando.set(false);
        this.error.set((e.error as ErrorApi | undefined)?.mensaje ?? 'No se pudo reiniciar los datos de prueba.');
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

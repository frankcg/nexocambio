import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AdminOperacionesService } from '../../../core/services/admin-operaciones.service';
import { AdminAuthService } from '../../../core/admin-auth/admin-auth.service';
import { ToastService } from '../../../shared/components/toast/toast.service';
import { EstadoOperacion, Operacion } from '../../../core/models/operacion.model';
import { ErrorApi } from '../../../core/models/error-api.model';
import { formatearFechaHora, formatearMoney } from '../../../shared/utils/moneda';

const MENSAJE_ERROR_RED = 'No pudimos conectar con el servidor. Revisa tu conexión e inténtalo otra vez.';

@Component({
  selector: 'app-admin-detalle',
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './admin-detalle.html',
})
export class AdminDetalle {
  private readonly admin = inject(AdminOperacionesService);
  private readonly adminAuth = inject(AdminAuthService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  private readonly id = this.ruta.snapshot.paramMap.get('id')!;

  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly operacion = signal<Operacion | null>(null);

  protected readonly enviando = signal(false);
  protected readonly errorAccion = signal('');
  protected readonly mostrandoMotivo = signal(false);
  protected readonly motivo = signal('');

  protected readonly siguienteAprobado = computed<EstadoOperacion | null>(() => {
    const estado = this.operacion()?.estado;
    if (estado === 'Pendiente de validación') return 'En proceso';
    if (estado === 'En proceso') return 'Procesada';
    return null;
  });

  protected readonly puedeAccionar = computed(() => this.siguienteAprobado() !== null);

  constructor() {
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.admin.obtener(this.id).subscribe({
      next: (o) => {
        this.operacion.set(o);
        this.cargando.set(false);
      },
      error: (e: HttpErrorResponse) => {
        if (e.status === 403) {
          this.adminAuth.salir();
          this.router.navigateByUrl('/admin/login');
          return;
        }
        this.error.set((e.error as ErrorApi | undefined)?.mensaje ?? 'No encontramos esta operación.');
        this.cargando.set(false);
      },
    });
  }

  protected aprobar(): void {
    const siguiente = this.siguienteAprobado();
    if (!siguiente) return;
    this.ejecutarCambio(siguiente);
  }

  protected mostrarFormularioRechazo(): void {
    this.mostrandoMotivo.set(true);
    this.errorAccion.set('');
  }

  protected cancelarRechazo(): void {
    this.mostrandoMotivo.set(false);
    this.motivo.set('');
    this.errorAccion.set('');
  }

  protected onCambioMotivo(valor: string): void {
    this.motivo.set(valor);
  }

  protected confirmarRechazo(): void {
    const motivo = this.motivo().trim();
    if (motivo.length < 3) {
      this.errorAccion.set('Escribe un motivo de al menos 3 caracteres.');
      return;
    }
    this.ejecutarCambio('Rechazada', motivo);
  }

  private ejecutarCambio(estado: EstadoOperacion, motivoRechazo?: string): void {
    this.errorAccion.set('');
    this.enviando.set(true);
    this.admin.cambiarEstado(this.id, estado, motivoRechazo).subscribe({
      next: (o) => {
        this.operacion.set(o);
        this.enviando.set(false);
        this.mostrandoMotivo.set(false);
        this.motivo.set('');
        this.toast.mostrar('Operación actualizada', `Ahora está "${estado}".`);
      },
      error: (e: HttpErrorResponse) => {
        this.enviando.set(false);
        if (e.status === 403) {
          this.adminAuth.salir();
          this.router.navigateByUrl('/admin/login');
          return;
        }
        this.errorAccion.set((e.error as ErrorApi | undefined)?.mensaje ?? MENSAJE_ERROR_RED);
      },
    });
  }

  protected origenTexto(): string {
    const o = this.operacion()?.origen;
    if (!o) return '—';
    return o.tipo === 'wallet' ? o.red : o.banco;
  }

  protected destinoTexto(): string {
    const d = this.operacion()?.destino;
    if (!d) return '—';
    return d.tipo === 'banco' ? `${d.banco} · ${d.tipo_cuenta} · ${d.numero} · ${d.titular}` : `${d.red} · ${d.direccion}`;
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

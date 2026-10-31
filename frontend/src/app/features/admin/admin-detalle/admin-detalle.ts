import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AdminOperacionesService } from '../../../core/services/admin-operaciones.service';
import { AdminAuthService } from '../../../core/admin-auth/admin-auth.service';
import { ToastService } from '../../../shared/components/toast/toast.service';
import { EstadoOperacion, Operacion } from '../../../core/models/operacion.model';
import { ErrorApi } from '../../../core/models/error-api.model';
import { ValidacionesService } from '../../../core/services/validaciones.service';
import { Validacion } from '../../../core/models/validacion.model';
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
  private readonly validacionesSvc = inject(ValidacionesService);
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

  // ------------------------------------------------------------ NexoGuard
  /** Última validación automática de la operación (null si no tiene). */
  protected readonly validacion = signal<Validacion | null>(null);
  protected readonly guardEnRevision = computed(() => this.validacion()?.estado === 'en_revision');
  protected readonly guardEnCurso = computed(() => this.validacion()?.estado === 'en_curso');

  /** Tabla «Declarado en la operación vs. Leído por el agente». */
  protected readonly comparativa = computed(() => {
    const o = this.operacion();
    const v = this.validacion();
    const ex = v?.extraccion;
    if (!o || !ex) return [];
    const res = (regla: string) => v.verificaciones?.find((r) => r.regla === regla)?.resultado ?? 'no_concluyente';
    const destino = o.origen.tipo === 'wallet' ? 'Billetera NexoCambio' : 'Cuenta NexoCambio';
    return [
      { campo: 'Monto', declarado: this.monto(o.monto_origen, o.moneda_origen), leido: ex.monto != null ? `${ex.monto.toFixed(2)} ${ex.moneda ?? ''}` : '—', resultado: res('monto') },
      { campo: 'Moneda', declarado: o.moneda_origen, leido: ex.moneda ?? '—', resultado: res('moneda') },
      { campo: 'Destino', declarado: destino, leido: [ex.destinatario, ex.cuenta_destino].filter(Boolean).join(' · ') || '—', resultado: res('cuenta_destino') },
      { campo: 'N.º de operación', declarado: o.numero_transferencia || '—', leido: ex.numero_operacion ?? '—', resultado: res('numero_operacion_unico') },
      { campo: 'Fecha', declarado: o.fecha_operacion.slice(0, 10), leido: ex.fecha ?? '—', resultado: res('fecha') },
      { campo: 'Banco de origen', declarado: this.origenTexto(), leido: ex.banco_origen ?? '—', resultado: res('banco_origen') },
    ];
  });

  protected readonly puedeAccionar = computed(() => this.siguienteAprobado() !== null && !this.guardEnCurso());

  private recarga: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    inject(DestroyRef).onDestroy(() => this.recarga && clearTimeout(this.recarga));
    this.cargar();
  }

  /** `silencioso`: refresco automático, sin esqueleto de carga. */
  protected cargar(silencioso = false): void {
    if (!silencioso) this.cargando.set(true);
    this.error.set(null);
    if (this.recarga) clearTimeout(this.recarga);
    this.validacionesSvc.obtenerAdmin(this.id).subscribe({
      next: (r) => {
        this.validacion.set(r.validaciones[0] ?? null);
        // Mientras NexoGuard valida, la pantalla se actualiza sola hasta tener el análisis
        if (this.validacion()?.estado === 'en_curso') this.recarga = setTimeout(() => this.cargar(true), 4000);
      },
      error: () => this.validacion.set(null), // 404: operación sin validación automática
    });
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
    if (this.guardEnRevision()) {
      this.decidirNexoguard('aprobar');
      return;
    }
    const siguiente = this.siguienteAprobado();
    if (!siguiente) return;
    this.ejecutarCambio(siguiente);
  }

  protected mostrarFormularioRechazo(): void {
    this.mostrandoMotivo.set(true);
    this.errorAccion.set('');
    const v = this.validacion();
    if (this.guardEnRevision() && v && !this.motivo()) {
      const falla = v.verificaciones?.find((r) => r.resultado === 'no_cumple' && r.gravedad !== 'informativa');
      this.motivo.set(v.motivo_sugerido || falla?.detalle || '');
    }
  }

  /** La decisión del operador reanuda el workflow NexoGuard (SendTaskSuccess) en lugar del PATCH directo. */
  private decidirNexoguard(decision: 'aprobar' | 'rechazar', motivo?: string): void {
    this.errorAccion.set('');
    this.enviando.set(true);
    this.validacionesSvc.decidir(this.id, decision, motivo).subscribe({
      next: (r) => {
        this.enviando.set(false);
        this.mostrandoMotivo.set(false);
        this.motivo.set('');
        this.toast.mostrar('Decisión registrada', r.mensaje);
        this.recarga = setTimeout(() => this.cargar(true), 3000); // el workflow aplica la decisión en ~1-2 s
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
    if (this.guardEnRevision()) {
      this.decidirNexoguard('rechazar', motivo);
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

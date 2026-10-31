import { ChangeDetectionStrategy, Component, DestroyRef, OnInit, inject, input, output, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ValidacionesService } from '../../../core/services/validaciones.service';
import { ValidacionCliente } from '../../../core/models/validacion.model';

const INTERVALO_MS = 3000;
const MAX_CONSULTAS = 40; // ~2 minutos; luego el cliente ve el resultado en Mis operaciones
const PASOS = ['Leyendo tu comprobante', 'Verificando los datos', 'Evaluando la operación'];

/**
 * Tarjeta de NexoGuard para el cliente: consulta GET /validaciones/{id} cada 3 s mientras la
 * validación automática está en curso y muestra el resultado. Si la operación no tiene
 * validación (404, p. ej. operaciones anteriores a NexoGuard) no muestra nada.
 */
@Component({
  selector: 'app-estado-nexoguard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './estado-nexoguard.html',
})
export class EstadoNexoguard implements OnInit {
  private readonly validaciones = inject(ValidacionesService);
  private readonly destroyRef = inject(DestroyRef);

  readonly idOperacion = input.required<string>();
  /** Se emite una vez cuando la validación termina, para que la página recargue la operación. */
  readonly terminada = output<ValidacionCliente>();

  protected readonly PASOS = PASOS;
  protected readonly validacion = signal<ValidacionCliente | null>(null);
  protected readonly pasoAnimado = signal(0);
  protected readonly agotado = signal(false);

  private consultas = 0;
  private temporizador: ReturnType<typeof setTimeout> | null = null;
  private animacion: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    this.animacion = setInterval(() => this.pasoAnimado.update((p) => Math.min(p + 1, PASOS.length - 1)), 2500);
    this.destroyRef.onDestroy(() => {
      if (this.temporizador) clearTimeout(this.temporizador);
      if (this.animacion) clearInterval(this.animacion);
    });
    this.consultar();
  }

  private consultar(): void {
    this.consultas++;
    this.validaciones.obtener(this.idOperacion()).subscribe({
      next: (v) => {
        const anterior = this.validacion()?.estado;
        this.validacion.set(v);
        if (v.estado === 'finalizada') {
          if (anterior !== 'finalizada') this.terminada.emit(v);
          return;
        }
        this.programar();
      },
      // 404: todavía no se registró (el workflow tarda ~1 s en iniciar) o la operación no tiene validación
      error: (e: HttpErrorResponse) => (e.status === 404 && this.consultas <= 3 ? this.programar() : undefined),
    });
  }

  private programar(): void {
    if (this.consultas >= MAX_CONSULTAS) {
      this.agotado.set(true);
      return;
    }
    this.temporizador = setTimeout(() => this.consultar(), INTERVALO_MS);
  }
}

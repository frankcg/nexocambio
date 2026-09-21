import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';

const DURACION_PASO_MS = 4500;

@Component({
  selector: 'app-como-funciona',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './como-funciona.html',
})
export class ComoFunciona {
  protected readonly pasoActual = signal(0);
  private intervalo: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this.reiniciarIntervalo();
    inject(DestroyRef).onDestroy(() => this.detener());
  }

  protected elegirPaso(i: number): void {
    this.pasoActual.set(i);
    this.reiniciarIntervalo();
  }

  private reiniciarIntervalo(): void {
    this.detener();
    this.intervalo = setInterval(() => this.pasoActual.update((p) => (p + 1) % 3), DURACION_PASO_MS);
  }

  private detener(): void {
    if (this.intervalo) clearInterval(this.intervalo);
    this.intervalo = null;
  }
}

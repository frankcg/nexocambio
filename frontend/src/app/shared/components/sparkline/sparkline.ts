import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

@Component({
  selector: 'app-sparkline',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './sparkline.html',
})
export class Sparkline {
  readonly valores = input.required<number[]>();
  readonly ancho = input(120);
  readonly alto = input(34);
  readonly area = input(false);
  readonly grilla = input(false);
  readonly punto = input(false);
  readonly color = input('var(--accent)');

  protected readonly datos = computed(() => {
    const vals = this.valores();
    const w = this.ancho();
    const h = this.alto();
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const pad = (max - min) * 0.12 || max * 0.001;
    const lo = min - pad;
    const hi = max + pad;
    const x = (i: number) => (i / (vals.length - 1)) * w;
    const y = (v: number) => h - ((v - lo) / (hi - lo)) * h;
    const puntos = vals.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`);
    const areaPath = `M0,${h} L${puntos.join(' L')} L${w},${h} Z`;
    const lineasGrilla = [0.2, 0.5, 0.8].map((f) => h * f);
    const ultimoX = x(vals.length - 1);
    const ultimoY = y(vals.at(-1)!);
    return { puntos: puntos.join(' '), areaPath, lineasGrilla, ultimoX, ultimoY };
  });
}

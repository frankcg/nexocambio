import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { MercadoSimuladoService } from '../../mercado-simulado.service';
import { formatearMonto } from '../../../../shared/utils/moneda';

const PASOS_COMPARADOR = [1000, 2500, 5000, 10000, 20000, 30000];

@Component({
  selector: 'app-comparador',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './comparador.html',
})
export class Comparador {
  private readonly mercado = inject(MercadoSimuladoService);

  protected readonly monto = signal(5000);
  protected readonly resultado = computed(() => this.mercado.calcularComparacion(this.monto()));

  protected readonly etiquetaMonto = computed(() => `S/ ${formatearMonto(this.monto(), 'PEN').replace(/\.00$/, '')}`);
  protected readonly textoBanco = computed(() => `US$ ${formatearMonto(this.resultado().banco, 'USD')}`);
  protected readonly textoNexo = computed(() => `US$ ${formatearMonto(this.resultado().nexo, 'USD')}`);
  protected readonly textoTcBanco = computed(() => this.formatearTc(this.resultado().tcBanco));
  protected readonly textoTcNexo = computed(() => this.formatearTc(this.resultado().tcNexo));
  protected readonly textoAhorro = computed(() => `S/ ${formatearMonto(this.resultado().ahorroPEN, 'PEN')}`);

  protected readonly barras = computed(() => {
    const max = this.mercado.calcularComparacion(PASOS_COMPARADOR.at(-1)!).ahorroPEN;
    const montoActual = this.monto();
    const masCercano = PASOS_COMPARADOR.reduce((mejor, v) => (Math.abs(v - montoActual) < Math.abs(mejor - montoActual) ? v : mejor), PASOS_COMPARADOR[0]);
    return PASOS_COMPARADOR.map((v) => {
      const ahorro = this.mercado.calcularComparacion(v).ahorroPEN;
      return {
        valor: v,
        actual: v === masCercano,
        alturaPorcentaje: (ahorro / max) * 100,
        etiquetaAhorro: `S/ ${formatearMonto(ahorro, 'PEN').replace(/\.00$/, '')}`,
        etiquetaMonto: v >= 1000 ? `${v % 1000 ? (v / 1000).toFixed(1) : v / 1000}k` : String(v),
      };
    });
  });

  protected cambiarMonto(valor: string): void {
    this.monto.set(Number(valor));
  }

  private formatearTc(v: number): string {
    return new Intl.NumberFormat('es-PE', { minimumFractionDigits: 3, maximumFractionDigits: 3 }).format(v);
  }
}

import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Modo } from '../../../../core/theme/theme.service';
import { Sparkline } from '../../../../shared/components/sparkline/sparkline';
import { MercadoSimuladoService } from '../../mercado-simulado.service';

@Component({
  selector: 'app-mercado-en-vivo',
  imports: [Sparkline],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './mercado-en-vivo.html',
})
export class MercadoEnVivo {
  private readonly mercado = inject(MercadoSimuladoService);

  protected readonly tab = signal<Modo>('casa');
  protected readonly filas = computed(() => this.mercado.filasDe(this.tab()));

  protected cambiarTab(tab: Modo): void {
    this.tab.set(tab);
  }

  protected cotizarFila(monedaA: string, monedaB: string): void {
    this.mercado.pedirPar(this.tab(), monedaB, monedaA);
  }
}

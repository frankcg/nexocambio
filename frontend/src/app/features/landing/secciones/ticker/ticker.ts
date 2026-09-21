import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { MercadoSimuladoService } from '../../mercado-simulado.service';

@Component({
  selector: 'app-ticker',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './ticker.html',
})
export class Ticker {
  private readonly mercado = inject(MercadoSimuladoService);
  protected readonly items = computed(() => this.mercado.itemsTicker());
}

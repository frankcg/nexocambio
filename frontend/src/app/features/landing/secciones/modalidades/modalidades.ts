import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MercadoSimuladoService } from '../../mercado-simulado.service';
import { MODOS_QUOTER } from '../../modos-quoter';

@Component({
  selector: 'app-modalidades',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './modalidades.html',
})
export class Modalidades {
  private readonly mercado = inject(MercadoSimuladoService);

  protected cotizar(modo: 'casa' | 'cripto'): void {
    const cfg = MODOS_QUOTER[modo];
    this.mercado.pedirPar(modo, cfg.def[0], cfg.def[1]);
    document.getElementById('quoter')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

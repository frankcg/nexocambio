import { ChangeDetectionStrategy, Component, DestroyRef, inject } from '@angular/core';
import { Footer } from '../../layout/footer/footer';
import { HeroCotizador } from './secciones/hero-cotizador/hero-cotizador';
import { FranjaBancos } from './secciones/franja-bancos/franja-bancos';
import { Ticker } from './secciones/ticker/ticker';
import { MercadoEnVivo } from './secciones/mercado-en-vivo/mercado-en-vivo';
import { MercadoSimuladoService } from './mercado-simulado.service';

@Component({
  imports: [Footer, HeroCotizador, FranjaBancos, Ticker, MercadoEnVivo],
  selector: 'app-landing',
  providers: [MercadoSimuladoService],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './landing.html',
})
export class Landing {
  private readonly mercado = inject(MercadoSimuladoService);

  constructor() {
    this.mercado.iniciar();
    inject(DestroyRef).onDestroy(() => this.mercado.detener());
  }
}

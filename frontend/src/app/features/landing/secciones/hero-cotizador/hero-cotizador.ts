import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../../../core/auth/auth.service';
import { CotizacionesService } from '../../../../core/services/cotizaciones.service';
import { DraftCotizacionService } from '../../../../core/draft/draft-cotizacion.service';
import { ThemeService, Modo } from '../../../../core/theme/theme.service';
import { ToastService } from '../../../../shared/components/toast/toast.service';
import { Sparkline } from '../../../../shared/components/sparkline/sparkline';
import { Cotizacion } from '../../../../core/models/cotizacion.model';
import { MONEDAS_CASA, Moneda } from '../../../../core/models/catalogos.model';
import { formatearMonto, parsearMonto } from '../../../../shared/utils/moneda';
import { MercadoSimuladoService } from '../../mercado-simulado.service';
import { MODOS_QUOTER } from '../../modos-quoter';

const VALIDEZ_SEG = 300;

@Component({
  selector: 'app-hero-cotizador',
  imports: [Sparkline],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './hero-cotizador.html',
})
export class HeroCotizador {
  private readonly cotizaciones = inject(CotizacionesService);
  private readonly draft = inject(DraftCotizacionService);
  private readonly auth = inject(AuthService);
  private readonly theme = inject(ThemeService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);
  private readonly mercado = inject(MercadoSimuladoService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly modo = this.theme.modo;
  protected readonly monedaOrigen = signal<Moneda>('PEN');
  protected readonly monedaDestino = signal<Moneda>('USD');
  protected readonly montoTexto = signal('1,000.00');
  protected readonly cotizacion = signal<Cotizacion | null>(null);
  protected readonly errorMensaje = signal('');
  protected readonly cargando = signal(false);
  protected readonly segundosRestantes = signal(VALIDEZ_SEG);

  protected readonly monedasOrigen = computed(() => MODOS_QUOTER[this.modo()].from);
  protected readonly monedasDestino = computed(() => MODOS_QUOTER[this.modo()].to);
  protected readonly eyebrow = computed(() => MODOS_QUOTER[this.modo()].eyebrow);
  protected readonly tituloHtml = computed(() => MODOS_QUOTER[this.modo()].titulo);
  protected readonly lead = computed(() => MODOS_QUOTER[this.modo()].lead);

  protected readonly board = computed(() => this.mercado.boardDe(this.modo()));

  protected readonly vencida = computed(() => this.cotizacion() !== null && this.segundosRestantes() === 0);
  protected readonly textoTemporizador = computed(() =>
    this.vencida() ? 'Cotización vencida' : `Tasa válida por ${this.mmss(this.segundosRestantes())}`
  );
  protected readonly proporcionBarra = computed(() => this.segundosRestantes() / VALIDEZ_SEG);

  protected readonly textoFuente = computed(() => {
    const x = this.cotizacion();
    if (!x) return this.cargando() ? 'Cotizando…' : 'Tasas de demostración';
    if (x.fuente_tasas === 'en_vivo') return 'Tasas en vivo';
    if (x.fuente_tasas === 'cache') return 'Tasas en caché';
    return 'Tasas referenciales';
  });
  protected readonly fuenteEnVivo = computed(() => this.cotizacion()?.fuente_tasas === 'en_vivo');

  protected readonly textoTasa = computed(() => {
    const x = this.cotizacion();
    if (!x) return '—';
    const invertir = this.mercado.tasaMid(x.moneda_origen) < this.mercado.tasaMid(x.moneda_destino);
    const base = invertir ? x.moneda_destino : x.moneda_origen;
    const cotizada = invertir ? x.moneda_origen : x.moneda_destino;
    const valor = invertir ? 1 / x.tasa : x.tasa;
    const dec = valor >= 100 ? 2 : 4;
    return `1 ${base} = ${new Intl.NumberFormat('es-PE', { minimumFractionDigits: dec, maximumFractionDigits: dec }).format(valor)} ${cotizada}`;
  });

  protected readonly etiquetaTasa = computed(() => {
    const x = this.cotizacion();
    if (!x) return 'Tipo de cambio';
    if (x.modalidad === 'cripto') return (MONEDAS_CASA as readonly string[]).includes(x.moneda_origen) ? 'Precio de compra' : 'Precio de venta';
    if (x.moneda_origen === 'PEN') return 'Tipo de cambio venta';
    if (x.moneda_destino === 'PEN') return 'Tipo de cambio compra';
    return 'Tipo de cambio';
  });

  protected readonly textoMontoDestino = computed(() => {
    const x = this.cotizacion();
    return x ? formatearMonto(x.monto_destino, x.moneda_destino) : '—';
  });

  protected readonly ahorroTexto = computed(() => {
    const x = this.cotizacion();
    if (!x || x.modalidad !== 'casa') return null;
    if (x.moneda_origen !== 'PEN' && x.moneda_destino !== 'PEN') return null;
    const diff = this.mercado.ahorroFrenteABanco(x.monto_origen, x.moneda_origen, x.moneda_destino, x.monto_destino);
    if (diff < 0.5) return null;
    return `Recibes aprox. S/ ${formatearMonto(diff, 'PEN')} más que en un banco tradicional`;
  });

  private secuencia = 0;
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
  private temporizador: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this.theme.establecer('casa');
    this.solicitarCotizacion();
    this.destroyRef.onDestroy(() => {
      if (this.debounceTimer) clearTimeout(this.debounceTimer);
      this.detenerTemporizador();
    });

    effect(() => {
      const par = this.mercado.parPendiente();
      if (!par) return;
      this.theme.establecer(par.modo);
      const cfg = MODOS_QUOTER[par.modo];
      const origen = (cfg.from.includes(par.origen) ? par.origen : cfg.def[0]) as Moneda;
      const destino = (cfg.to.includes(par.destino) ? par.destino : cfg.def[1]) as Moneda;
      this.monedaOrigen.set(origen);
      this.monedaDestino.set(destino);
      const montoDefault = origen === 'PEN' ? 1000 : origen === 'USD' || origen === 'EUR' ? 500 : 100;
      this.montoTexto.set(formatearMonto(montoDefault, origen));
      this.solicitarCotizacion();
      this.mercado.consumirParPendiente();
    });
  }

  protected cambiarModo(modo: Modo): void {
    if (modo === this.modo()) return;
    this.theme.establecer(modo);
    const cfg = MODOS_QUOTER[modo];
    this.monedaOrigen.set(cfg.def[0] as Moneda);
    this.monedaDestino.set(cfg.def[1] as Moneda);
    this.solicitarCotizacion();
  }

  protected onInputMonto(valor: string): void {
    this.montoTexto.set(valor);
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => this.solicitarCotizacion(), 250);
  }

  protected onBlurMonto(): void {
    const v = parsearMonto(this.montoTexto());
    if (v > 0) this.montoTexto.set(formatearMonto(v, this.monedaOrigen()));
  }

  protected onFocusMonto(): void {
    const v = parsearMonto(this.montoTexto());
    this.montoTexto.set(v > 0 ? String(v) : '');
  }

  protected cambiarMonedaOrigen(moneda: string): void {
    this.monedaOrigen.set(moneda as Moneda);
    this.solicitarCotizacion();
  }

  protected cambiarMonedaDestino(moneda: string): void {
    this.monedaDestino.set(moneda as Moneda);
    this.solicitarCotizacion();
  }

  protected intercambiar(): void {
    const cfg = MODOS_QUOTER[this.modo()];
    const o = this.monedaOrigen();
    const d = this.monedaDestino();
    if (cfg.from.includes(d) && cfg.to.includes(o)) {
      this.monedaOrigen.set(d);
      this.monedaDestino.set(o);
    }
    const monto = this.cotizacion()?.monto_destino ?? parsearMonto(this.montoTexto());
    if (monto > 0) this.montoTexto.set(formatearMonto(monto, this.monedaOrigen()));
    this.solicitarCotizacion();
  }

  protected solicitarCotizacion(): void {
    const monto = parsearMonto(this.montoTexto());
    const o = this.monedaOrigen();
    const d = this.monedaDestino();
    let mensaje = '';
    if (o === d) mensaje = 'Elige monedas distintas para enviar y recibir.';
    else if (!(monto > 0)) mensaje = 'Ingresa un monto mayor a cero.';
    else if (monto * this.mercado.tasaMid(o) < 10) mensaje = 'El monto mínimo equivale a US$ 10.';

    this.errorMensaje.set(mensaje);
    if (mensaje) {
      this.cotizacion.set(null);
      this.detenerTemporizador();
      return;
    }

    const miSecuencia = ++this.secuencia;
    this.cargando.set(true);
    this.cotizaciones.cotizar({ modalidad: this.modo(), moneda_origen: o, moneda_destino: d, monto_origen: monto }).subscribe({
      next: (x) => {
        if (miSecuencia !== this.secuencia) return;
        this.cotizacion.set(x);
        this.cargando.set(false);
        this.iniciarTemporizador();
      },
      error: () => {
        if (miSecuencia !== this.secuencia) return;
        this.cargando.set(false);
        this.errorMensaje.set('No pudimos obtener la tasa. Inténtalo nuevamente.');
      },
    });
  }

  protected operarAhora(): void {
    const x = this.cotizacion();
    if (!x) return;
    if (this.vencida()) {
      this.solicitarCotizacion();
      this.toast.mostrar('Cotización actualizada', 'La tasa anterior venció. Revisa el nuevo monto.');
      return;
    }
    this.draft.guardar(x);
    if (this.auth.autenticado()) {
      this.router.navigateByUrl('/operar');
    } else {
      this.toast.mostrar('Inicia sesión para continuar', 'Guardamos tu cotización. Ingresa o crea tu cuenta para registrar la operación.');
      this.router.navigate(['/login'], { queryParams: { next: '/operar' } });
    }
  }

  private iniciarTemporizador(): void {
    this.detenerTemporizador();
    this.actualizarSegundos();
    this.temporizador = setInterval(() => this.actualizarSegundos(), 1000);
  }

  private detenerTemporizador(): void {
    if (this.temporizador) clearInterval(this.temporizador);
    this.temporizador = null;
  }

  private actualizarSegundos(): void {
    const x = this.cotizacion();
    if (!x) {
      this.segundosRestantes.set(0);
      return;
    }
    const restante = Math.max(0, Math.round((Date.parse(x.fecha_expiracion) - Date.now()) / 1000));
    this.segundosRestantes.set(restante);
  }

  private mmss(s: number): string {
    return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
  }
}

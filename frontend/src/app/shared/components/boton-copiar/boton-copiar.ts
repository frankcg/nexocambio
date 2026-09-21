import { ChangeDetectionStrategy, Component, input, signal } from '@angular/core';

@Component({
  selector: 'app-boton-copiar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './boton-copiar.html',
})
export class BotonCopiar {
  readonly valor = input.required<string>();

  protected readonly etiqueta = signal('Copiar');
  private temporizador: ReturnType<typeof setTimeout> | null = null;

  protected async copiar(): Promise<void> {
    try {
      await navigator.clipboard.writeText(this.valor());
      this.etiqueta.set('Copiado');
    } catch {
      this.etiqueta.set('Selecciónalo');
    }
    if (this.temporizador) clearTimeout(this.temporizador);
    this.temporizador = setTimeout(() => this.etiqueta.set('Copiar'), 1600);
  }
}

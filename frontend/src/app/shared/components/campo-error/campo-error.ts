import { ChangeDetectionStrategy, Component, effect, input, signal } from '@angular/core';
import { AbstractControl } from '@angular/forms';
import { primerMensajeError } from '../../validators/nexo-validators';

@Component({
  selector: 'app-campo-error',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (mensaje(); as m) {
      <small class="msg">{{ m }}</small>
    }
  `,
})
export class CampoError {
  readonly control = input.required<AbstractControl | null>();

  private readonly _mensaje = signal<string | null>(null);
  readonly mensaje = this._mensaje.asReadonly();

  constructor() {
    effect((onCleanup) => {
      const control = this.control();
      this._mensaje.set(primerMensajeError(control));
      if (!control) return;
      const suscripcion = control.events.subscribe(() => this._mensaje.set(primerMensajeError(control)));
      onCleanup(() => suscripcion.unsubscribe());
    });
  }
}

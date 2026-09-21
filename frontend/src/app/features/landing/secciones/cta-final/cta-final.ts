import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-cta-final',
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './cta-final.html',
})
export class CtaFinal {
  protected cotizarAhora(): void {
    const campo = document.getElementById('quoter');
    campo?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(() => document.getElementById('amt-from')?.focus({ preventScroll: true }), 500);
  }
}

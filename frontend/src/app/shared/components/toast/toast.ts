import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ToastService } from './toast.service';

@Component({
  selector: 'app-toast',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="toast" [class.show]="toast.actual() !== null" role="status" aria-live="polite">
      @if (toast.actual(); as t) {
        <b>{{ t.titulo }}</b>{{ t.cuerpo }}
      }
    </div>
  `,
})
export class Toast {
  protected readonly toast = inject(ToastService);
}

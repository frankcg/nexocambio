import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-stepper',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './stepper.html',
})
export class Stepper {
  readonly etiquetas = input.required<string[]>();
  readonly pasoActual = input.required<number>();
}

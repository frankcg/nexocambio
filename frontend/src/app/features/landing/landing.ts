import { ChangeDetectionStrategy, Component } from '@angular/core';
import { Footer } from '../../layout/footer/footer';

@Component({
  imports: [Footer],
  selector: 'app-landing',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './landing.scss',
  templateUrl: './landing.html',
})
export class Landing {}

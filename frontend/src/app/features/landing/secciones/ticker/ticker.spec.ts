import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Ticker } from './ticker';
import { MercadoSimuladoService } from '../../mercado-simulado.service';

describe('Ticker', () => {
  let component: Ticker;
  let fixture: ComponentFixture<Ticker>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Ticker],
      providers: [MercadoSimuladoService],
    }).compileComponents();

    fixture = TestBed.createComponent(Ticker);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

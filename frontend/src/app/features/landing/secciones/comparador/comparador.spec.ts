import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Comparador } from './comparador';
import { MercadoSimuladoService } from '../../mercado-simulado.service';

describe('Comparador', () => {
  let component: Comparador;
  let fixture: ComponentFixture<Comparador>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Comparador],
      providers: [MercadoSimuladoService],
    }).compileComponents();

    fixture = TestBed.createComponent(Comparador);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

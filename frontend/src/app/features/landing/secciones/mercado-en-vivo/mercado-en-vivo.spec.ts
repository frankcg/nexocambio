import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MercadoEnVivo } from './mercado-en-vivo';
import { MercadoSimuladoService } from '../../mercado-simulado.service';

describe('MercadoEnVivo', () => {
  let component: MercadoEnVivo;
  let fixture: ComponentFixture<MercadoEnVivo>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MercadoEnVivo],
      providers: [MercadoSimuladoService],
    }).compileComponents();

    fixture = TestBed.createComponent(MercadoEnVivo);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

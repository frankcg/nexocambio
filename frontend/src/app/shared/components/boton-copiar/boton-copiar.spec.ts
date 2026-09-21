import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BotonCopiar } from './boton-copiar';

describe('BotonCopiar', () => {
  let fixture: ComponentFixture<BotonCopiar>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BotonCopiar],
    }).compileComponents();

    fixture = TestBed.createComponent(BotonCopiar);
    fixture.componentRef.setInput('valor', '193-2458710-0-39');
    fixture.detectChanges();
  });

  it('muestra el valor y el botón Copiar', () => {
    expect(fixture.nativeElement.textContent).toContain('193-2458710-0-39');
    expect(fixture.nativeElement.textContent).toContain('Copiar');
  });
});

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormControl, Validators } from '@angular/forms';
import { CampoError } from './campo-error';

describe('CampoError', () => {
  let fixture: ComponentFixture<CampoError>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CampoError],
    }).compileComponents();

    fixture = TestBed.createComponent(CampoError);
  });

  it('no muestra mensaje si el control no ha sido tocado', () => {
    fixture.componentRef.setInput('control', new FormControl('', Validators.required));
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent.trim()).toBe('');
  });

  it('muestra el mensaje del primer error una vez tocado', () => {
    const control = new FormControl('', Validators.required);
    control.markAsTouched();
    fixture.componentRef.setInput('control', control);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Este campo es obligatorio.');
  });
});

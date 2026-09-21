import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Stepper } from './stepper';

describe('Stepper', () => {
  let fixture: ComponentFixture<Stepper>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Stepper],
    }).compileComponents();

    fixture = TestBed.createComponent(Stepper);
    fixture.componentRef.setInput('etiquetas', ['Uno', 'Dos', 'Tres']);
    fixture.componentRef.setInput('pasoActual', 1);
    fixture.detectChanges();
  });

  it('marca como "now" el paso actual', () => {
    const items = fixture.nativeElement.querySelectorAll('li');
    expect(items[0].classList.contains('done')).toBe(true);
    expect(items[1].classList.contains('now')).toBe(true);
    expect(items[2].classList.contains('done')).toBe(false);
  });
});

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Sparkline } from './sparkline';

describe('Sparkline', () => {
  let fixture: ComponentFixture<Sparkline>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Sparkline],
    }).compileComponents();

    fixture = TestBed.createComponent(Sparkline);
    fixture.componentRef.setInput('valores', [1, 2, 3, 2, 1]);
    fixture.detectChanges();
  });

  it('dibuja una polyline con un punto por valor', () => {
    const puntos = fixture.nativeElement.querySelector('polyline').getAttribute('points');
    expect(puntos.trim().split(' ').length).toBe(5);
  });
});

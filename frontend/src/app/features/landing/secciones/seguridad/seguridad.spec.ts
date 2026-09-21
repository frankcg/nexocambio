import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Seguridad } from './seguridad';

describe('Seguridad', () => {
  let component: Seguridad;
  let fixture: ComponentFixture<Seguridad>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Seguridad],
    }).compileComponents();

    fixture = TestBed.createComponent(Seguridad);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

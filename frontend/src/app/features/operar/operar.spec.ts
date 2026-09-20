import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Operar } from './operar';

describe('Operar', () => {
  let component: Operar;
  let fixture: ComponentFixture<Operar>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Operar],
    }).compileComponents();

    fixture = TestBed.createComponent(Operar);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

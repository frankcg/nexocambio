import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FranjaBancos } from './franja-bancos';

describe('FranjaBancos', () => {
  let component: FranjaBancos;
  let fixture: ComponentFixture<FranjaBancos>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FranjaBancos],
    }).compileComponents();

    fixture = TestBed.createComponent(FranjaBancos);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

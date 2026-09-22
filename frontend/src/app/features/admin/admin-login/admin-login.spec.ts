import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { AdminLogin } from './admin-login';
import { AdminAuthService } from '../../../core/admin-auth/admin-auth.service';

describe('AdminLogin', () => {
  let component: AdminLogin;
  let fixture: ComponentFixture<AdminLogin>;
  let adminAuth: AdminAuthService;
  let router: Router;

  beforeEach(async () => {
    sessionStorage.clear();
    await TestBed.configureTestingModule({
      imports: [AdminLogin],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(AdminLogin);
    component = fixture.componentInstance;
    adminAuth = TestBed.inject(AdminAuthService);
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('guarda la clave y navega a la cola de revisión al ingresar', () => {
    const navigateSpy = vi.spyOn(router, 'navigateByUrl');
    component['clave'].set('mi-clave-secreta');
    component['ingresar']();
    expect(adminAuth.autenticado()).toBe(true);
    expect(navigateSpy).toHaveBeenCalledWith('/admin/operaciones');
  });

  it('no hace nada si la clave está vacía', () => {
    const navigateSpy = vi.spyOn(router, 'navigateByUrl');
    component['clave'].set('   ');
    component['ingresar']();
    expect(adminAuth.autenticado()).toBe(false);
    expect(navigateSpy).not.toHaveBeenCalled();
  });
});

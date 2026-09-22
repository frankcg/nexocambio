import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AdminAuthService } from '../../../core/admin-auth/admin-auth.service';

@Component({
  selector: 'app-admin-login',
  imports: [FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './admin-login.html',
})
export class AdminLogin {
  private readonly adminAuth = inject(AdminAuthService);
  private readonly router = inject(Router);

  protected readonly clave = signal('');
  protected readonly mostrarClave = signal(false);

  protected ingresar(): void {
    const valor = this.clave().trim();
    if (!valor) return;
    this.adminAuth.iniciarSesion(valor);
    this.router.navigateByUrl('/admin/operaciones');
  }

  protected alternarMostrar(): void {
    this.mostrarClave.update((v) => !v);
  }
}

import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AdminAuthService } from '../../core/admin-auth/admin-auth.service';

@Component({
  selector: 'app-admin-header',
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './admin-header.html',
})
export class AdminHeader {
  protected readonly auth = inject(AdminAuthService);
  private readonly router = inject(Router);

  protected salir(): void {
    this.auth.salir();
    this.router.navigateByUrl('/admin/login');
  }
}

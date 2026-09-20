import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { ToastService } from '../../shared/components/toast/toast.service';

interface EnlaceNav {
  etiqueta: string;
  ruta?: string;
  fragmento?: string;
}

const ENLACES_AUTENTICADO: EnlaceNav[] = [
  { etiqueta: 'Cotizar', ruta: '/' },
  { etiqueta: 'Mis operaciones', ruta: '/operaciones' },
];

const ENLACES_ANONIMO: EnlaceNav[] = [
  { etiqueta: 'Tasas', fragmento: 'mercado' },
  { etiqueta: 'Cómo funciona', fragmento: 'como-funciona' },
  { etiqueta: 'Comparador', fragmento: 'ahorro' },
  { etiqueta: 'Seguridad', fragmento: 'seguridad' },
  { etiqueta: 'Ayuda', fragmento: 'faq' },
];

@Component({
  selector: 'app-header',
  imports: [RouterLink, RouterLinkActive],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './header.html',
})
export class Header {
  protected readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);

  protected readonly enlaces = computed<EnlaceNav[]>(() =>
    this.auth.autenticado() ? ENLACES_AUTENTICADO : ENLACES_ANONIMO
  );

  protected readonly primerNombre = computed(() => {
    const cliente = this.auth.cliente();
    if (!cliente) return '';
    return cliente.tipo_cliente === 'empresa' ? cliente.nombre : String(cliente.nombre ?? '').split(' ')[0];
  });

  protected salir(): void {
    this.auth.logout();
    this.toast.mostrar('Sesión cerrada', 'Hasta pronto.');
    this.router.navigate(['/']);
  }
}

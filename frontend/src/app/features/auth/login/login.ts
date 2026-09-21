import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../../core/auth/auth.service';
import { ClientesService } from '../../../core/services/clientes.service';
import { DraftCotizacionService } from '../../../core/draft/draft-cotizacion.service';
import { ToastService } from '../../../shared/components/toast/toast.service';
import { CampoError } from '../../../shared/components/campo-error/campo-error';
import { emailValidator } from '../../../shared/validators/nexo-validators';
import { ErrorApi } from '../../../core/models/error-api.model';

const MENSAJE_ERROR_RED = 'No pudimos conectar con el servidor. Revisa tu conexión e inténtalo otra vez.';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, RouterLink, CampoError],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './login.html',
})
export class Login {
  private readonly fb = inject(FormBuilder);
  private readonly clientes = inject(ClientesService);
  private readonly auth = inject(AuthService);
  private readonly draft = inject(DraftCotizacionService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly siguiente = this.ruta.snapshot.queryParamMap.get('next');
  protected readonly hayDraft = computed(() => this.draft.cotizacion() !== null);

  protected readonly enviando = signal(false);
  protected readonly errorGeneral = signal<string | null>(null);
  protected readonly mostrarPassword = signal(false);

  protected readonly registroQueryParams = this.siguiente ? { next: this.siguiente } : {};

  protected readonly form = this.fb.nonNullable.group({
    correo: ['', [Validators.required, emailValidator()]],
    password: ['', [Validators.required]],
  });

  protected enviar(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.errorGeneral.set(null);
    this.enviando.set(true);
    const { correo, password } = this.form.getRawValue();
    this.clientes.login({ correo, password }).subscribe({
      next: (respuesta) => {
        this.auth.login(respuesta.token, respuesta.cliente);
        const nombre =
          respuesta.cliente.tipo_cliente === 'empresa'
            ? respuesta.cliente.nombre
            : String(respuesta.cliente.nombre ?? '').split(' ')[0];
        this.toast.mostrar('Bienvenido', `Hola, ${nombre}.`);
        this.router.navigateByUrl(this.siguiente ?? (this.hayDraft() ? '/operar' : '/operaciones'));
      },
      error: (error: HttpErrorResponse) => {
        const cuerpo = error.error as ErrorApi | undefined;
        this.errorGeneral.set(cuerpo?.mensaje ?? MENSAJE_ERROR_RED);
        this.enviando.set(false);
      },
    });
  }

  protected alternarPassword(): void {
    this.mostrarPassword.update((v) => !v);
  }
}

import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../../core/auth/auth.service';
import { ClientesService } from '../../../core/services/clientes.service';
import { DraftCotizacionService } from '../../../core/draft/draft-cotizacion.service';
import { CampoError } from '../../../shared/components/campo-error/campo-error';
import { Stepper } from '../../../shared/components/stepper/stepper';
import {
  ACTIVIDADES,
  Actividad,
  OCUPACIONES,
  Ocupacion,
  TIPOS_DOCUMENTO_PERSONA,
} from '../../../core/models/catalogos.model';
import { RegistroEmpresaRequest, RegistroPersonaRequest } from '../../../core/models/cliente.model';
import { ErrorApi } from '../../../core/models/error-api.model';
import {
  documentoValidator,
  emailValidator,
  mayorEdadValidator,
  password2Validator,
  passwordValidator,
  rucValidator,
  telefonoValidator,
} from '../../../shared/validators/nexo-validators';

type TipoCliente = 'persona' | 'empresa';

const PASOS_PERSONA = ['Tipo de cliente', 'Identidad', 'Contacto', 'Acceso'];
const PASOS_EMPRESA = ['Tipo de cliente', 'Empresa', 'Representante', 'Acceso'];

const SUBTITULOS_PERSONA: (string | null)[] = [
  null,
  'Tal como figura en tu documento.',
  'Te avisaremos aquí cuando tu operación cambie de estado.',
  'Con estos datos iniciarás sesión.',
];

const SUBTITULOS_EMPRESA: (string | null)[] = [
  null,
  'Datos según SUNAT.',
  'Persona autorizada para operar a nombre de la empresa.',
  'El correo del representante será el usuario de la empresa.',
];

const CAMPOS_PASO_PERSONA: string[][] = [
  [],
  ['nombres', 'apellidos', 'tipo_documento', 'numero_documento', 'fecha_nacimiento'],
  ['telefono', 'ocupacion', 'pep'],
  ['correo', 'password', 'password2'],
];

const CAMPOS_PASO_EMPRESA: string[][] = [
  [],
  ['ruc', 'razon_social', 'actividad'],
  ['rep_nombres', 'rep_tipo_documento', 'rep_numero_documento', 'rep_cargo', 'telefono'],
  ['correo', 'password', 'password2'],
];

const MENSAJE_ERROR_RED = 'No pudimos conectar con el servidor. Revisa tu conexión e inténtalo otra vez.';
const MENSAJE_TERMINOS = 'Para crear tu cuenta debes aceptar los términos y la declaración de origen de fondos.';

@Component({
  selector: 'app-registro',
  imports: [ReactiveFormsModule, RouterLink, CampoError, Stepper],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './registro.html',
})
export class Registro {
  protected readonly OCUPACIONES = OCUPACIONES;
  protected readonly ACTIVIDADES = ACTIVIDADES;
  protected readonly TIPOS_DOCUMENTO_PERSONA = TIPOS_DOCUMENTO_PERSONA;

  private readonly fb = inject(FormBuilder);
  private readonly clientes = inject(ClientesService);
  private readonly auth = inject(AuthService);
  private readonly draft = inject(DraftCotizacionService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly siguiente = this.ruta.snapshot.queryParamMap.get('next');

  protected readonly paso = signal(0);
  protected readonly enviando = signal(false);
  protected readonly errorGeneral = signal<string | null>(null);
  protected readonly mostrarPassword = signal(false);
  protected readonly mostrarPassword2 = signal(false);
  protected readonly registrado = signal<{ nombre: string } | null>(null);

  private readonly tipoDocumentoControl = this.fb.nonNullable.control<'DNI' | 'CE' | 'Pasaporte'>('DNI');
  private readonly repTipoDocumentoControl = this.fb.nonNullable.control<'DNI' | 'CE' | 'Pasaporte'>('DNI');

  protected readonly form = this.fb.nonNullable.group(
    {
      tipo_cliente: this.fb.nonNullable.control<TipoCliente>('persona'),
      nombres: ['', Validators.required],
      apellidos: ['', Validators.required],
      tipo_documento: this.tipoDocumentoControl,
      numero_documento: ['', [Validators.required, documentoValidator(() => this.tipoDocumentoControl.value)]],
      fecha_nacimiento: ['', [Validators.required, mayorEdadValidator()]],
      telefono: ['', [Validators.required, telefonoValidator()]],
      ocupacion: [''],
      pep: this.fb.nonNullable.control<'No' | 'Sí'>('No'),
      ruc: ['', [Validators.required, rucValidator()]],
      razon_social: ['', Validators.required],
      actividad: [''],
      rep_nombres: ['', Validators.required],
      rep_tipo_documento: this.repTipoDocumentoControl,
      rep_numero_documento: ['', [Validators.required, documentoValidator(() => this.repTipoDocumentoControl.value)]],
      rep_cargo: ['', Validators.required],
      correo: ['', [Validators.required, emailValidator()]],
      password: ['', [Validators.required, passwordValidator()]],
      password2: ['', Validators.required],
      terminos: [false],
    },
    { validators: [password2Validator('password', 'password2')] }
  );

  protected readonly tipoCliente = computed(() => this.paso() >= 0 && this.form.controls.tipo_cliente.value);

  constructor() {
    this.tipoDocumentoControl.valueChanges.subscribe(() =>
      this.form.controls.numero_documento.updateValueAndValidity()
    );
    this.repTipoDocumentoControl.valueChanges.subscribe(() =>
      this.form.controls.rep_numero_documento.updateValueAndValidity()
    );
  }

  protected pasos(): string[] {
    return this.form.controls.tipo_cliente.value === 'empresa' ? PASOS_EMPRESA : PASOS_PERSONA;
  }

  protected esUltimoPaso(): boolean {
    return this.paso() === this.pasos().length - 1;
  }

  protected tituloPaso(): string {
    const titulo = this.pasos()[this.paso()];
    return titulo === 'Tipo de cliente' ? '¿Cómo vas a operar?' : titulo;
  }

  protected subtituloPaso(): string | null {
    const lista = this.form.controls.tipo_cliente.value === 'empresa' ? SUBTITULOS_EMPRESA : SUBTITULOS_PERSONA;
    return lista[this.paso()];
  }

  private camposDelPaso(): string[] {
    const lista = this.form.controls.tipo_cliente.value === 'empresa' ? CAMPOS_PASO_EMPRESA : CAMPOS_PASO_PERSONA;
    return lista[this.paso()];
  }

  protected atras(): void {
    this.errorGeneral.set(null);
    this.paso.update((p) => p - 1);
  }

  protected continuar(): void {
    this.errorGeneral.set(null);
    if (this.paso() === 0) {
      this.paso.set(1);
      return;
    }

    const campos = this.camposDelPaso();
    let primerInvalido: string | null = null;
    for (const nombre of campos) {
      const control = this.form.controls[nombre as keyof typeof this.form.controls];
      control.markAsTouched();
      if (control.invalid && !primerInvalido) primerInvalido = nombre;
    }
    if (primerInvalido) return;

    if (!this.esUltimoPaso()) {
      this.paso.update((p) => p + 1);
      return;
    }

    if (!this.form.controls.terminos.value) {
      this.errorGeneral.set(MENSAJE_TERMINOS);
      return;
    }

    this.enviarRegistro();
  }

  private enviarRegistro(): void {
    const d = this.form.getRawValue();
    const payload: RegistroPersonaRequest | RegistroEmpresaRequest =
      d.tipo_cliente === 'persona'
        ? {
            tipo_cliente: 'persona',
            nombres: d.nombres,
            apellidos: d.apellidos,
            tipo_documento: d.tipo_documento,
            numero_documento: d.numero_documento,
            fecha_nacimiento: d.fecha_nacimiento,
            telefono: d.telefono,
            ocupacion: (d.ocupacion || undefined) as Ocupacion | undefined,
            pep: d.pep === 'Sí',
            correo: d.correo,
            password: d.password,
          }
        : {
            tipo_cliente: 'empresa',
            razon_social: d.razon_social,
            tipo_documento: 'RUC',
            numero_documento: d.ruc,
            actividad: (d.actividad || undefined) as Actividad | undefined,
            telefono: d.telefono,
            correo: d.correo,
            password: d.password,
            representante: {
              nombre: d.rep_nombres,
              tipo_documento: d.rep_tipo_documento,
              numero_documento: d.rep_numero_documento,
              cargo: d.rep_cargo,
            },
          };
    const nombreMostrado = d.tipo_cliente === 'persona' ? `${d.nombres} ${d.apellidos}` : d.razon_social;

    this.enviando.set(true);
    this.clientes.registrar(payload).subscribe({
      next: () => {
        this.clientes.login({ correo: payload.correo, password: payload.password }).subscribe({
          next: (respuesta) => {
            this.auth.login(respuesta.token, respuesta.cliente);
            this.registrado.set({ nombre: nombreMostrado });
          },
          error: () => {
            this.registrado.set({ nombre: nombreMostrado });
          },
        });
      },
      error: (error: HttpErrorResponse) => {
        const cuerpo = error.error as ErrorApi | undefined;
        this.errorGeneral.set(cuerpo?.mensaje ?? MENSAJE_ERROR_RED);
        this.enviando.set(false);
      },
    });
  }

  protected destinoFinal(): string {
    if (this.siguiente) return this.siguiente;
    return this.draft.cotizacion() ? '/operar' : '/';
  }

  protected etiquetaDestinoFinal(): string {
    return this.destinoFinal() === '/operar' ? 'Continuar con mi operación' : 'Hacer mi primera cotización';
  }

  protected alternarPassword(): void {
    this.mostrarPassword.update((v) => !v);
  }

  protected alternarPassword2(): void {
    this.mostrarPassword2.update((v) => !v);
  }
}

import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

const REGEX_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const REGEX_TELEFONO = /^9\d{8}$/;
const REGEX_DNI = /^\d{8}$/;
const REGEX_CE = /^[A-Za-z0-9]{9,12}$/;
const REGEX_PASAPORTE = /^[A-Za-z0-9]{6,12}$/;
const REGEX_RUC = /^(10|15|17|20)\d{9}$/;
const REGEX_CUENTA = /^\d{10,20}$/;
const REGEX_WALLET = /^[A-Za-z0-9]{26,64}$/;

export const MENSAJES_ERROR: Record<string, string> = {
  required: 'Este campo es obligatorio.',
  emailInvalido: 'Ingresa un correo válido, por ejemplo nombre@correo.com.',
  telefonoInvalido: 'El celular debe tener 9 dígitos y empezar con 9.',
  documentoInvalidoDNI: 'El DNI tiene 8 dígitos.',
  documentoInvalidoCE: 'El carné de extranjería tiene entre 9 y 12 caracteres.',
  documentoInvalidoPasaporte: 'Revisa el número de pasaporte.',
  rucInvalido: 'El RUC tiene 11 dígitos y empieza con 10 o 20.',
  menorEdad: 'Debes ser mayor de edad para registrarte.',
  passwordDebil: 'Usa al menos 8 caracteres, con letras y números.',
  passwordNoCoincide: 'Las contraseñas no coinciden.',
  cuentaInvalida: 'Ingresa entre 10 y 20 dígitos (número de cuenta o CCI).',
  walletInvalida: 'La dirección no parece válida. Cópiala directamente desde tu billetera.',
  terminosNoAceptados: 'Para crear tu cuenta debes aceptar los términos y la declaración de origen de fondos.',
};

export function primerMensajeError(control: AbstractControl | null): string | null {
  if (!control || !control.errors || !(control.touched || control.dirty)) {
    return null;
  }
  const clave = Object.keys(control.errors)[0];
  return MENSAJES_ERROR[clave] ?? null;
}

export function emailValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    if (!control.value) return null;
    return REGEX_EMAIL.test(control.value) ? null : { emailInvalido: true };
  };
}

export function telefonoValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    if (!control.value) return null;
    return REGEX_TELEFONO.test(control.value) ? null : { telefonoInvalido: true };
  };
}

export function documentoValidator(obtenerTipo: () => 'DNI' | 'CE' | 'Pasaporte' | string): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    if (!control.value) return null;
    const tipo = obtenerTipo();
    if (tipo === 'DNI') return REGEX_DNI.test(control.value) ? null : { documentoInvalidoDNI: true };
    if (tipo === 'CE') return REGEX_CE.test(control.value) ? null : { documentoInvalidoCE: true };
    return REGEX_PASAPORTE.test(control.value) ? null : { documentoInvalidoPasaporte: true };
  };
}

export function rucValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    if (!control.value) return null;
    return REGEX_RUC.test(control.value) ? null : { rucInvalido: true };
  };
}

export function mayorEdadValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    if (!control.value) return null;
    const nacimiento = new Date(control.value);
    if (Number.isNaN(nacimiento.getTime())) return null;
    const edadMs = Date.now() - nacimiento.getTime();
    const edadAnios = edadMs / (1000 * 60 * 60 * 24 * 365.25);
    return edadAnios >= 18 ? null : { menorEdad: true };
  };
}

export function passwordValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const valor: string = control.value ?? '';
    if (!valor) return null;
    const tieneLetra = /[A-Za-z]/.test(valor);
    const tieneDigito = /\d/.test(valor);
    return valor.length >= 8 && tieneLetra && tieneDigito ? null : { passwordDebil: true };
  };
}

export function password2Validator(campoPassword: string, campoPassword2: string): ValidatorFn {
  return (grupo: AbstractControl): ValidationErrors | null => {
    const password = grupo.get(campoPassword)?.value;
    const password2 = grupo.get(campoPassword2)?.value;
    const control2 = grupo.get(campoPassword2);
    if (!control2 || !password2) return null;
    if (password !== password2) {
      control2.setErrors({ ...control2.errors, passwordNoCoincide: true });
      return { passwordNoCoincide: true };
    }
    if (control2.hasError('passwordNoCoincide')) {
      const { passwordNoCoincide: _sinUso, ...resto } = control2.errors ?? {};
      control2.setErrors(Object.keys(resto).length ? resto : null);
    }
    return null;
  };
}

export function cuentaBancariaValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    if (!control.value) return null;
    const limpio = String(control.value).replace(/[\s-]/g, '');
    return REGEX_CUENTA.test(limpio) ? null : { cuentaInvalida: true };
  };
}

export function walletValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    if (!control.value) return null;
    return REGEX_WALLET.test(control.value) ? null : { walletInvalida: true };
  };
}

export function terminosAceptadosValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    return control.value === true ? null : { terminosNoAceptados: true };
  };
}

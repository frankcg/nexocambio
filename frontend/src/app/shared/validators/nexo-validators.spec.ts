import { FormControl, FormGroup } from '@angular/forms';
import {
  cuentaBancariaValidator,
  documentoValidator,
  emailValidator,
  mayorEdadValidator,
  passwordValidator,
  password2Validator,
  rucValidator,
  telefonoValidator,
  terminosAceptadosValidator,
  walletValidator,
} from './nexo-validators';

describe('emailValidator', () => {
  it('acepta un correo válido', () => {
    expect(emailValidator()(new FormControl('demo@nexocambio.pe'))).toBeNull();
  });
  it('rechaza un correo sin dominio', () => {
    expect(emailValidator()(new FormControl('demo@nexocambio'))).toEqual({ emailInvalido: true });
  });
});

describe('telefonoValidator', () => {
  it('acepta un celular peruano válido', () => {
    expect(telefonoValidator()(new FormControl('987654321'))).toBeNull();
  });
  it('rechaza un número que no empieza con 9', () => {
    expect(telefonoValidator()(new FormControl('187654321'))).toEqual({ telefonoInvalido: true });
  });
});

describe('documentoValidator', () => {
  it('valida DNI de 8 dígitos', () => {
    const v = documentoValidator(() => 'DNI');
    expect(v(new FormControl('12345678'))).toBeNull();
    expect(v(new FormControl('123'))).toEqual({ documentoInvalidoDNI: true });
  });
  it('valida CE de 9 a 12 caracteres', () => {
    const v = documentoValidator(() => 'CE');
    expect(v(new FormControl('ABC123456'))).toBeNull();
    expect(v(new FormControl('AB'))).toEqual({ documentoInvalidoCE: true });
  });
  it('valida pasaporte de 6 a 12 caracteres', () => {
    const v = documentoValidator(() => 'Pasaporte');
    expect(v(new FormControl('AB1234'))).toBeNull();
    expect(v(new FormControl('AB'))).toEqual({ documentoInvalidoPasaporte: true });
  });
});

describe('rucValidator', () => {
  it('acepta un RUC que empieza en 20', () => {
    expect(rucValidator()(new FormControl('20123456789'))).toBeNull();
  });
  it('rechaza un RUC que no empieza en 10/15/17/20', () => {
    expect(rucValidator()(new FormControl('99123456789'))).toEqual({ rucInvalido: true });
  });
});

describe('mayorEdadValidator', () => {
  it('acepta a alguien mayor de 18 años', () => {
    const hace20anios = new Date();
    hace20anios.setFullYear(hace20anios.getFullYear() - 20);
    expect(mayorEdadValidator()(new FormControl(hace20anios.toISOString().slice(0, 10)))).toBeNull();
  });
  it('rechaza a alguien menor de 18 años', () => {
    const hace10anios = new Date();
    hace10anios.setFullYear(hace10anios.getFullYear() - 10);
    expect(mayorEdadValidator()(new FormControl(hace10anios.toISOString().slice(0, 10)))).toEqual({ menorEdad: true });
  });
});

describe('passwordValidator', () => {
  it('acepta una contraseña con letras y números de 8+ caracteres', () => {
    expect(passwordValidator()(new FormControl('Demo1234'))).toBeNull();
  });
  it('rechaza una contraseña solo numérica', () => {
    expect(passwordValidator()(new FormControl('12345678'))).toEqual({ passwordDebil: true });
  });
  it('rechaza una contraseña corta', () => {
    expect(passwordValidator()(new FormControl('Ab1'))).toEqual({ passwordDebil: true });
  });
});

describe('password2Validator', () => {
  it('no marca error si las contraseñas coinciden', () => {
    const grupo = new FormGroup({
      password: new FormControl('Demo1234'),
      password2: new FormControl('Demo1234'),
    });
    expect(password2Validator('password', 'password2')(grupo)).toBeNull();
    expect(grupo.get('password2')?.errors).toBeNull();
  });
  it('marca error en password2 si no coinciden', () => {
    const grupo = new FormGroup({
      password: new FormControl('Demo1234'),
      password2: new FormControl('Otra123'),
    });
    expect(password2Validator('password', 'password2')(grupo)).toEqual({ passwordNoCoincide: true });
    expect(grupo.get('password2')?.errors).toEqual({ passwordNoCoincide: true });
  });
});

describe('cuentaBancariaValidator', () => {
  it('acepta una cuenta de 10 a 20 dígitos, limpiando guiones', () => {
    expect(cuentaBancariaValidator()(new FormControl('191-234567-0-12'))).toBeNull();
  });
  it('rechaza una cuenta demasiado corta', () => {
    expect(cuentaBancariaValidator()(new FormControl('12345'))).toEqual({ cuentaInvalida: true });
  });
});

describe('walletValidator', () => {
  it('acepta una dirección alfanumérica de 26 a 64 caracteres', () => {
    expect(walletValidator()(new FormControl('a'.repeat(34)))).toBeNull();
  });
  it('rechaza una dirección demasiado corta', () => {
    expect(walletValidator()(new FormControl('abc123'))).toEqual({ walletInvalida: true });
  });
});

describe('terminosAceptadosValidator', () => {
  it('acepta cuando el checkbox está marcado', () => {
    expect(terminosAceptadosValidator()(new FormControl(true))).toBeNull();
  });
  it('rechaza cuando el checkbox no está marcado', () => {
    expect(terminosAceptadosValidator()(new FormControl(false))).toEqual({ terminosNoAceptados: true });
  });
});

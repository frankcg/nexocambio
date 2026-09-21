import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';

const BANCOS_FRANJA = ['BCP', 'Interbank', 'BBVA', 'Scotiabank', 'BanBif', 'Pichincha'];

function calcularAbierto(): { abierto: boolean; texto: string } {
  const partes = Object.fromEntries(
    new Intl.DateTimeFormat('en-US', { timeZone: 'America/Lima', weekday: 'short', hour: 'numeric', minute: 'numeric', hour12: false })
      .formatToParts(new Date())
      .map((p) => [p.type, p.value])
  );
  const h = (Number(partes['hour']) % 24) + Number(partes['minute']) / 60;
  const wd = partes['weekday'];
  const abierto = (['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].includes(wd) && h >= 9 && h < 18) || (wd === 'Sat' && h >= 9 && h < 13);
  const texto = abierto
    ? `Abierto ahora · hasta las ${wd === 'Sat' ? '13:00' : '18:00'}`
    : 'Fuera de horario · procesamos al abrir (Lun–Vie 9–18, Sáb 9–13)';
  return { abierto, texto };
}

@Component({
  selector: 'app-franja-bancos',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './franja-bancos.html',
})
export class FranjaBancos {
  protected readonly BANCOS = BANCOS_FRANJA;
  protected readonly estado = signal(calcularAbierto());

  constructor() {
    const intervalo = setInterval(() => this.estado.set(calcularAbierto()), 60000);
    inject(DestroyRef).onDestroy(() => clearInterval(intervalo));
  }
}

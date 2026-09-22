import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { DraftCotizacionService } from './draft-cotizacion.service';
import { ToastService } from '../../shared/components/toast/toast.service';

export const operarGuard: CanActivateFn = () => {
  const draft = inject(DraftCotizacionService);
  const router = inject(Router);

  if (draft.cotizacion()) return true;

  inject(ToastService).mostrar('Primero cotiza', 'Elige monedas y monto en el cotizador para iniciar una operación.');
  return router.createUrlTree(['/']);
};

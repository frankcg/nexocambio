import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./features/landing/landing').then((m) => m.Landing),
  },
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login/login').then((m) => m.Login),
  },
  {
    path: 'registro',
    loadComponent: () => import('./features/auth/registro/registro').then((m) => m.Registro),
  },
  {
    path: 'operar',
    canActivate: [authGuard],
    loadComponent: () => import('./features/operar/operar').then((m) => m.Operar),
  },
  {
    path: 'operaciones',
    canActivate: [authGuard],
    loadComponent: () => import('./features/operaciones/lista/lista').then((m) => m.Lista),
  },
  {
    path: 'operaciones/:id',
    canActivate: [authGuard],
    loadComponent: () => import('./features/operaciones/detalle/detalle').then((m) => m.Detalle),
  },
  { path: '**', redirectTo: '' },
];

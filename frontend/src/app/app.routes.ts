import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth.guard';
import { adminGuard } from './core/admin-auth/admin.guard';
import { operarGuard } from './core/draft/operar.guard';

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
    canActivate: [authGuard, operarGuard],
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
  {
    path: 'admin/login',
    loadComponent: () => import('./features/admin/admin-login/admin-login').then((m) => m.AdminLogin),
  },
  {
    path: 'admin/operaciones',
    canActivate: [adminGuard],
    loadComponent: () => import('./features/admin/admin-lista/admin-lista').then((m) => m.AdminLista),
  },
  {
    path: 'admin/operaciones/:id',
    canActivate: [adminGuard],
    loadComponent: () => import('./features/admin/admin-detalle/admin-detalle').then((m) => m.AdminDetalle),
  },
  { path: 'admin', redirectTo: 'admin/operaciones' },
  { path: '**', redirectTo: '' },
];

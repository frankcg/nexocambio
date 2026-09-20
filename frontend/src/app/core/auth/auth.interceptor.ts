import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const token = auth.token();

  const esLogin = req.url.includes('/login');
  const conAuth = token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;

  return next(conAuth).pipe(
    catchError((error) => {
      if (error?.status === 401 && !esLogin) {
        auth.logout();
        router.navigate(['/login'], { queryParams: { next: router.url } });
      }
      return throwError(() => error);
    })
  );
};

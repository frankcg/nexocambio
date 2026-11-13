# NexoCambio — Casa de cambio de divisas y cripto 100 % digital (Cloud Computing · UTEC Posgrado)

MVP serverless en AWS Academy (Learner Lab, us-east-1): **API Gateway (HTTP API) + 3 microservicios AWS Lambda (Python 3.12) + DynamoDB + S3 + CloudWatch/SNS**.
Cada microservicio tiene su propia base de datos.

| Microservicio | Rutas | Base de datos propia |
|---|---|---|
| Cotizaciones | `POST /cotizar` | DynamoDB `nexo-<stage>-tasas`, `nexo-<stage>-cotizaciones` (TTL) |
| Clientes / Auth | `POST /registro`, `POST /login`, `GET /clientes/{id}` | DynamoDB `nexo-<stage>-clientes` |
| Operaciones | `POST/GET /operaciones`, `GET /operaciones/{id}`, `POST /operaciones/{id}/comprobante`, `PATCH /operaciones/{id}/estado` (back-office) | DynamoDB `nexo-<stage>-operaciones` + S3 privado |

## Desplegar (AWS CloudShell dentro del Learner Lab)
```bash
git clone <este repo> && cd nexocambio
ALERT_EMAIL=tu@correo.com ./scripts/deploy.sh      # imprime ApiUrl, sitio web y clave de back-office
./scripts/destroy.sh                                # al terminar: elimina todo
```
Parámetros útiles: `STAGE` (por defecto `dev`), `AWS_REGION` (por defecto `us-east-1`), `USAR_TASAS_EN_VIVO=false` para usar tasas referenciales, `USAR_HTTPS=true` para poner una distribución CloudFront delante del sitio (opt-in, ver abajo).

> Requisitos del Lab: el rol `LabRole` debe existir (es el que usan las Lambdas) y S3 debe permitir un bucket con política pública para el sitio web.
>
> **HTTPS del sitio:** `deploy.sh` imprime `Sitio web (HTTPS)` al terminar. Por defecto es el endpoint REST de S3 (`https://<bucket>.s3.<región>.amazonaws.com/index.html`, certificado válido de Amazon): la API ya era HTTPS y, como la app usa rutas con hash, basta con que el bucket sea público. Hay que abrir la URL **con `/index.html`** (en la raíz S3 devuelve 403), y por eso `frontend/src/index.html` no lleva `<base href>`: con él, Angular reescribía la barra de direcciones a `/#/...` y un F5 rompía la página. El endpoint `http://...s3-website-...` (HTTP) sigue funcionando pero no está cifrado.
>
> **CloudFront (opcional):** con `USAR_HTTPS=true` se crea una distribución con su dominio/certificado `*.cloudfront.net` (sin ACM ni dominio propio) y `SitioWebHttpsUrl` apunta a ella; la primera creación tarda 10-20 min. En AWS Academy Learner Lab **no funciona**: el rol `voclabs` no tiene `cloudfront:CreateDistribution` y el stack falla con `AccessDenied` (hace rollback solo). Úsalo únicamente en una cuenta que sí lo permita.
>
> Las credenciales de sesión del Learner Lab expiran cada pocas horas. Si `deploy.sh` o `destroy.sh` fallan a mitad de camino por eso, basta con refrescar las credenciales y volver a correr el mismo script: ambos son seguros de reintentar.

## Probar sin AWS
```bash
pip install -r requirements-dev.txt
python -m pytest                       # 57 pruebas (AWS simulado con moto)
python scripts/servidor_local.py       # API en http://localhost:8787 con cliente demo demo@nexocambio.pe / Demo1234
cd frontend && npm ci && npx ng serve  # app Angular en http://localhost:4200 (lee la API de public/config.json)
```
Postman: importar `postman/NexoCambio.postman_collection.json`, definir `baseUrl` (`ApiUrl` del despliegue) y `adminKey`, y ejecutar en el Runner (33 requests, 62 verificaciones; incluye el flujo de back-office: listar, detalle, aprobar y rechazar).
Catálogo de la API (OpenAPI 3.0): `docs/openapi.json` (spec) y `docs/openapi.html` (ábrelo en el navegador, Swagger UI con el spec embebido). Es solo documentación: describe el contrato real, pero el API Gateway sigue definido con eventos SAM en `template.yaml`, no con este spec.
Regenerar: `python scripts/generar_postman.py` · `python docs/generar_openapi.py` · `python docs/costos.py` · `python docs/generar_diagrama.py`.

## Exposición: preparar datos e imágenes limpios
Hacerlo **el mismo día de la exposición**, desde la raíz del repo. Los comprobantes llevan la fecha del día en que se
generan, y NexoGuard manda a revisión un comprobante con más de 1 día de diferencia respecto a la fecha **UTC** de la
operación (en Lima, desde las 19:00 ya es el día siguiente en UTC).

**1. Credenciales.** En el Learner Lab: *AWS Details* → *AWS CLI* → copiar el bloque completo en
`C:\Users\<usuario>\.aws\credentials` (con `[default]` y `aws_session_token`).

**2. Preparar todo con un comando:**
```bash
python scripts/preparar_exposicion.py --ensayo
```
El script lee la `ApiUrl` del stack `nexocambio-dev` y, en orden:
- reinicia los datos de prueba: validaciones (el control de duplicados), banco simulado, operaciones y comprobantes
  en S3. Los clientes se conservan, incluido `demo@nexocambio.pe`;
- regenera las imágenes de `tests/fixtures/comprobantes/` con la fecha de hoy (semilla 101);
- registra en el banco simulado los depósitos del 01, 02, 03, 06 y 07, y **comprueba que el banco los tenga**;
- con `--ensayo`, ejecuta el caso 1 por la API, confirma que sale verde y vuelve a reiniciar y registrar los depósitos;
- regenera la carpeta 6 de Postman con comprobantes de hoy (se omite con `--sin-postman`);
- comprueba que el tema SNS tenga una suscripción confirmada.

Si algo falla (credenciales vencidas, stack inexistente, depósito no registrado, caso 1 no verde), se detiene con un
mensaje ✗. Al final imprime el comando del caso 9 (depósito tardío) con la URL correcta.

**3. En Postman**, borrar la colección anterior y **volver a importar** `postman/NexoCambio.postman_collection.json`.
No usar `scripts/generar_postman.py` para esto: rehace la colección **sin** la carpeta 6.

### Primera prueba en verde (caso 1 de `docs/final/guion_demo.md`)
En la web, como `demo@nexocambio.pe` / `Demo1234`: **Casa de Cambio**, envías **PEN 1,000**, recibes USD, banco de
origen **BCP**, cuenta de destino **Interbank · Ahorros · 8983141592653**, N° de operación **vacío**, y subir
`01_ok_bcp_pen_1000.png`. En ~10 s la tarjeta pasa de «Validando…» a «¡Comprobante validado!».

Sale en verde solo si se cumplen tres condiciones: su depósito está en el banco, su número no se usó antes y la fecha
es de hoy. `preparar_exposicion.py` deja las tres listas.
- **Después del script y antes de la demo web, no usar el botón «Reiniciar datos de prueba» ni la 6.0 de Postman**:
  ambos borran los depósitos del banco y el caso verde pasaría a revisión por «sin depósito». Si hay que reiniciar,
  volver a ejecutar `python scripts/preparar_exposicion.py`.
- Si también se mostrará Postman, hacerlo **después** de la demo web.
- Esperar ~20 s entre casos: Groq gratuito admite ~3 comprobantes por minuto. Si responde 429, el workflow reintenta
  solo, pero el resultado tarda más.

### NexoGuard con Postman (carpeta 6)
Verificado el 12-nov-2026 contra AWS: con la 6.0 al inicio, la carpeta 6 pasó completa dos veces seguidas con los
mismos comprobantes (rutas verde, roja y amarilla).
- **Variables de la colección:** `baseUrl` = `ApiUrl`, `adminKey` y `bancoKey` (de `.secrets/`).
- **Orden:** carpeta 2 (deja `{{token}}`) y luego la 6, empezando por **6.0 Reiniciar datos de prueba**. La 6.0 vacía
  las validaciones y el banco; los pasos «2b» vuelven a registrar sus propios depósitos. Así la carpeta se puede repetir
  sin el rechazo por «número ya usado».
- **Duración:** unos 5-6 min. La 6.7 (sin depósito) tarda ~2 min porque el workflow consulta 4 veces al banco antes de
  pasar a revisión.
- **Al terminar:** la 6.0 usa `incluir_operaciones: false`, así que las operaciones quedan en la lista, y además borró
  los depósitos de la demo web. Para dejar todo listo otra vez, ejecutar de nuevo `preparar_exposicion.py`.

## Frontend
`frontend/` es la app Angular (standalone components, signals, formularios reactivos, rutas con hash) que consume los 3 microservicios. La URL de la API se lee en runtime de `frontend/public/config.json`; `deploy.sh` compila la app (`ng build`) y genera ese archivo con la URL real antes de publicar en S3. `frontend-legacy/index.html` es el prototipo original, mantenido solo como referencia de diseño y textos.

## Notas de seguridad / límites del MVP
JWT HS256 propio (en producción: Cognito + Secrets Manager); contraseñas con PBKDF2; secretos en variables de entorno de Lambda; sin procesamiento real de fondos; los estados se avanzan con `PATCH /operaciones/{id}/estado` (cabecera `x-admin-key`).

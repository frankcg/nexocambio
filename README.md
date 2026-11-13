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

## Exposición: NexoGuard con Postman (carpeta 6)
Verificado el 12-nov-2026 contra AWS: con la 6.0 al inicio, la carpeta 6 pasó completa dos veces seguidas con los
mismos comprobantes (rutas verde, roja y amarilla). El guion de la demo web está en `docs/final/guion_demo.md`.
- **Regenerar los comprobantes el día de la exposición.** Van incrustados con fecha fija y NexoGuard manda a revisión
  un comprobante con más de 1 día de antigüedad respecto a la fecha **UTC** de la operación (en Lima, a partir de las
  19:00 ya es el día siguiente). La 6.0 no lo corrige: ejecutar `python postman/generar_nexoguard.py`, hacer commit y
  **volver a importar** la colección en Postman (una copia vieja sigue con los comprobantes anteriores).
- **Variables de la colección:** `baseUrl` = `ApiUrl` del despliegue, `adminKey` y `bancoKey` (de `.secrets/`).
- **Orden:** carpeta 2 (deja `{{token}}`) y luego la 6, empezando por **6.0 Reiniciar datos de prueba**. La 6.0 vacía
  las validaciones (el control de duplicados), reinicia el banco simulado y detiene las ejecuciones en curso; los pasos
  «2b» vuelven a registrar los depósitos. Así se puede repetir la carpeta sin el rechazo por «número ya usado».
- **Duración:** unos 5-6 min. La 6.7 (sin depósito) tarda ~2 min porque el workflow consulta 4 veces al banco antes de
  pasar a revisión. Groq gratuito admite ~3 comprobantes por minuto: si responde 429, el workflow reintenta solo.
- **Al terminar:** la 6.0 usa `incluir_operaciones: false`, así que las operaciones de corridas anteriores quedan en
  la lista. Para limpiarlas, usar «Reiniciar datos de prueba» en el back-office con operaciones incluidas.
- **Credenciales:** las del Learner Lab expiran; actualizarlas en `~/.aws/credentials` antes de empezar.
- **Correo de NexoGuard:** el tema SNS `nexo-<stage>-nexoguard` necesita una suscripción confirmada para que lleguen
  los avisos de revisión.

## Frontend
`frontend/` es la app Angular (standalone components, signals, formularios reactivos, rutas con hash) que consume los 3 microservicios. La URL de la API se lee en runtime de `frontend/public/config.json`; `deploy.sh` compila la app (`ng build`) y genera ese archivo con la URL real antes de publicar en S3. `frontend-legacy/index.html` es el prototipo original, mantenido solo como referencia de diseño y textos.

## Notas de seguridad / límites del MVP
JWT HS256 propio (en producción: Cognito + Secrets Manager); contraseñas con PBKDF2; secretos en variables de entorno de Lambda; sin procesamiento real de fondos; los estados se avanzan con `PATCH /operaciones/{id}/estado` (cabecera `x-admin-key`).

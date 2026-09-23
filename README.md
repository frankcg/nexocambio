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
Parámetros útiles: `STAGE` (por defecto `dev`), `AWS_REGION` (por defecto `us-east-1`), `USAR_TASAS_EN_VIVO=false` para usar tasas referenciales, `USAR_HTTPS=false` para desactivar CloudFront y servir el sitio solo por HTTP directo desde S3 (si el Lab lo restringe).

> Requisitos del Lab: el rol `LabRole` debe existir (es el que usan las Lambdas) y S3 debe permitir un bucket con política pública para el sitio web. Por defecto el sitio se sirve por HTTPS a través de una distribución CloudFront (dominio y certificado `*.cloudfront.net`, sin necesidad de ACM ni dominio propio); `deploy.sh` imprime esa URL al terminar. La primera vez que se crea (o se cambia) la distribución, el despliegue puede tardar 10-20 minutos en propagar — es normal, solo hay que esperar.
>
> Las credenciales de sesión del Learner Lab expiran cada pocas horas. Si `deploy.sh` o `destroy.sh` fallan a mitad de camino por eso (mientras CloudFront sigue propagando del lado de AWS), basta con refrescar las credenciales y volver a correr el mismo script: ambos son seguros de reintentar.

## Probar sin AWS
```bash
pip install -r requirements-dev.txt
python -m pytest                       # 54 pruebas (AWS simulado con moto)
python scripts/servidor_local.py       # API en http://localhost:8787 con cliente demo demo@nexocambio.pe / Demo1234
cd frontend && npm ci && npx ng serve  # app Angular en http://localhost:4200 (lee la API de public/config.json)
```
Postman: importar `postman/NexoCambio.postman_collection.json`, definir `baseUrl` (`ApiUrl` del despliegue) y `adminKey`, y ejecutar en el Runner (20 requests, 27 verificaciones).
Regenerar: `python scripts/generar_postman.py` · `python docs/costos.py` · `python docs/generar_diagrama.py`.

## Frontend
`frontend/` es la app Angular (standalone components, signals, formularios reactivos, rutas con hash) que consume los 3 microservicios. La URL de la API se lee en runtime de `frontend/public/config.json`; `deploy.sh` compila la app (`ng build`) y genera ese archivo con la URL real antes de publicar en S3. `frontend-legacy/index.html` es el prototipo original, mantenido solo como referencia de diseño y textos.

## Notas de seguridad / límites del MVP
JWT HS256 propio (en producción: Cognito + Secrets Manager); contraseñas con PBKDF2; secretos en variables de entorno de Lambda; sin procesamiento real de fondos; los estados se avanzan con `PATCH /operaciones/{id}/estado` (cabecera `x-admin-key`).

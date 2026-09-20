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
Parámetros útiles: `STAGE` (por defecto `dev`), `AWS_REGION` (por defecto `us-east-1`), `USAR_TASAS_EN_VIVO=false` para usar tasas referenciales.

> Requisitos del Lab: el rol `LabRole` debe existir (es el que usan las Lambdas) y S3 debe permitir un bucket con política pública para el sitio web. Si CloudFront está habilitado en su Lab puede ponerse delante del bucket web para obtener HTTPS.

## Probar sin AWS
```bash
pip install -r requirements-dev.txt
python -m pytest                       # 54 pruebas (AWS simulado con moto)
python scripts/servidor_local.py       # API en http://localhost:8787 con cliente demo demo@nexocambio.pe / Demo1234
python scripts/configurar_front.py frontend/index.html /tmp/front.html http://localhost:8787   # abrir /tmp/front.html
```
Postman: importar `postman/NexoCambio.postman_collection.json`, definir `baseUrl` (`ApiUrl` del despliegue) y `adminKey`, y ejecutar en el Runner (20 requests, 27 verificaciones).
Regenerar: `python scripts/generar_postman.py` · `python docs/costos.py` · `python docs/generar_diagrama.py`.

## Frontend
`frontend/index.html` es el prototipo del equipo. Funciona en modo demo y, con `CONFIG.API` apuntando a la API, consume los microservicios (`deploy.sh` lo configura y publica en S3).

## Notas de seguridad / límites del MVP
JWT HS256 propio (en producción: Cognito + Secrets Manager); contraseñas con PBKDF2; secretos en variables de entorno de Lambda; sin procesamiento real de fondos; los estados se avanzan con `PATCH /operaciones/{id}/estado` (cabecera `x-admin-key`).

# NexoCambio

Casa de cambio de divisas y cripto (proyecto de Cloud Computing, UTEC Posgrado).
Backend serverless en AWS: API Gateway (HTTP API) + 3 Lambdas Python 3.12 + DynamoDB + S3.

## Estructura
- services/{cotizaciones,clientes,operaciones}/app.py: microservicios (cada uno con su BD)
- layer/python/nexo_common.py: código compartido (JWT, hash, respuestas)
- template.yaml: CloudFormation. scripts/: deploy.sh, destroy.sh, servidor_local.py, configurar_front.py
- tests/: pytest con moto. postman/: colección de la API
- frontend-legacy/index.html: prototipo original (referencia de pantallas y diseño, ya no se despliega)
- frontend/: app Angular (componentes standalone, signals, formularios reactivos, rutas con hash)

## Comandos
- Pruebas backend: `python -m pytest`
- API local (sin AWS): `python scripts/servidor_local.py` (http://localhost:8787,
  cliente demo demo@nexocambio.pe / Demo1234)
- Front: `cd frontend && npm ci && npx ng serve` (puerto 4200; lee la API de `public/config.json`)
- Tests del front: `cd frontend && npx ng test`

## Reglas
- No modificar el backend sin consultarlo. Si el front necesita un cambio en la API, proponerlo primero.
- Todo texto de interfaz en español. Trabajar en pasos pequeños y hacer un commit por cada uno.
- Nunca guardar secretos ni claves en el repositorio (.secrets/ está en .gitignore).

## Contrato de la API
JSON. Errores: {mensaje, codigo}. Rutas protegidas: Authorization: Bearer <token>.
Si responde 401 en una ruta protegida: limpiar sesión e ir a login.
- POST /cotizar {modalidad:"casa"|"cripto", moneda_origen, moneda_destino, monto_origen} -> 201
  {id_cotizacion, tasa, tasa_preferencial, monto_destino, fecha_expiracion}. Vigencia 5 min.
- POST /registro (persona o empresa; ver frontend-legacy) -> 201 {id_cliente}; 409 si duplicado
- POST /login {correo, password} -> {token, expira_en, cliente}
- POST /operaciones {id_cotizacion, origen, destino} -> 201 (una cotización se usa una sola vez)
- POST /operaciones/{id}/comprobante {nombre_archivo, content_type, contenido_base64,
  numero_transferencia?}: JPG/PNG/WEBP/PDF, máx. 4 MB
- GET /operaciones -> {operaciones, total}; GET /operaciones/{id} -> con historial y comprobante_url
Estados: Pendiente de validación, En proceso, Procesada, Rechazada.

Back-office (simulado, protegido con cabecera x-admin-key en vez de JWT; sin ella la ruta
PATCH queda deshabilitada):
- GET /operaciones/admin -> {operaciones, total} de TODOS los clientes (Scan, excluye borradores)
- GET /operaciones/{id}/admin -> detalle de cualquier operación, con comprobante_url
- PATCH /operaciones/{id}/estado {estado:"En proceso"|"Procesada"|"Rechazada", motivo_rechazo?}
  Transiciones: Pendiente de validación -> {En proceso, Rechazada}; En proceso -> {Procesada, Rechazada}.

## Frontend Angular
Migración de frontend-legacy/index.html completa: landing, login, registro (persona/empresa),
wizard de operar, mis operaciones y detalle, con los textos, validaciones y tokens de color del
prototipo portados tal cual. Simplificación conocida frente al prototipo: el "mercado en vivo"
de la landing (sparklines/random walk) es decorativo y vive en `MercadoSimuladoService`, sin
relación con las tasas reales de `/cotizar`. Tests: `nexo-validators` tiene cobertura unitaria
completa; los flujos críticos (cotizador, wizard de operar, mis operaciones, detalle, back-office)
tienen tests de integración con `HttpTestingController` contra el contrato real de la API.

### Back-office (/admin)
Sección separada del flujo de cliente: auth propia (`AdminAuthService`, guarda la clave
x-admin-key en sessionStorage, sin JWT ni cuentas individuales) y su propio header
(`AdminHeader`, sin nav de cliente). Rutas: `/admin/login`, `/admin/operaciones` (cola con
filtro por estado), `/admin/operaciones/:id` (detalle + aprobar/rechazar). Un usuario de
back-office solo puede llegar a este flujo; nunca ve las pantallas de cliente.
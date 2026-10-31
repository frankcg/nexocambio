# PARTE C — IMPLEMENTACIÓN DEL MVP EN AWS

> Proyecto Final · NexoGuard · Nivel 4.
> Los recuadros **[PENDIENTE: …]** marcan las capturas y los datos reales que se completan después del despliegue en AWS Academy.

## 1. Resumen de lo implementado

| Componente | Implementación | Archivos |
|---|---|---|
| Workflow agéntico | AWS Step Functions **Standard**, 17 estados: ruta predefinida, `Retry`/`Catch` por estado, revisión humana con `waitForTaskToken` e integraciones directas con SNS | `statemachine/nexoguard.asl.json` |
| Agente Extractor | Lambda Python 3.12 + Groq `qwen/qwen3.8-27b` (visión, sin memoria) | `services/guard_extraer/app.py` |
| Verificación | Lambda Python 3.12 con 7 reglas deterministas y detección de duplicados (GSI) | `services/guard_verificar/app.py` |
| Agente de Riesgo | Lambda Python 3.12 + Groq `openai/gpt-oss-20b` (texto, sin memoria) con barreras de decisión | `services/guard_riesgo/app.py` |
| API Validaciones | Microservicio nuevo (4 rutas + 3 acciones internas) con su BD `nexo-validaciones` | `services/validaciones/app.py` |
| Cambios en Operaciones | `StartExecution` al adjuntar el comprobante y acción interna `aplicar_decision` (historial con actor) | `services/operaciones/app.py` |
| Cliente Groq | Cliente HTTP sin dependencias en la Lambda Layer; errores `GroqLimite`/`GroqError` que el `Retry` de Step Functions reconoce | `layer/python/nexo_groq.py` |
| Infraestructura como código | CloudFormation: 1 tabla, 4 Lambdas, máquina de estados, SNS, 4 rutas, alarma | `template.yaml`, `scripts/deploy.sh` |
| Frontend | Angular 22: validación en vivo para el cliente; cola y revisión asistida en el back-office | `frontend/src/app/…` (ver sección 4) |
| Pruebas | 74 pruebas de backend (pytest + moto) y 65 de frontend (Vitest) | `tests/`, `*.spec.ts` |
| Evidencia API | Colección Postman con la carpeta «6. NexoGuard» (30 requests) | `postman/` |

Todo el código se escribió con asistencia de IA (Claude) a partir del diseño de la Parte B, tal como permite el enunciado.

## 2. BackEnd: workflow, APIs y BD

### 2.1 Workflow NexoGuard en Step Functions

La definición `statemachine/nexoguard.asl.json` se despliega con `DefinitionS3Location`, y CloudFormation reemplaza los ARN de las Lambdas y del tema SNS mediante `DefinitionSubstitutions`. Decisiones de implementación:

- **Errores con nombre:** si Groq responde 429 (límite por minuto), la Lambda lanza `GroqLimite` y el estado reintenta a los 20 s, 40 s y 80 s. Si aun así falla, el `Catch` envía la operación a revisión humana: nunca se pierde.
- **Revisión humana:** `EsperarRevision` invoca a la API Validaciones con `$$.Task.Token`. El token se guarda en DynamoDB y el workflow queda pausado, sin costo, hasta 72 h. La decisión del operador llega por `POST /validaciones/{id}/decision`, que ejecuta `SendTaskSuccess`.
- **Notificaciones:** `NotificarRevision`, `NotificarCumplimiento` y `RevisionVencida` publican directamente en SNS, sin Lambda intermedia.
- **Sin dependencia circular:** Operaciones recibe el ARN de la máquina de estados armado con `!Sub`, porque la máquina de estados ya referencia a Operaciones.

**[PENDIENTE: captura del grafo de Step Functions (Workflow Studio) y de una ejecución exitosa por cada ruta: verde, amarilla y roja.]**

### 2.2 Barreras de decisión implementadas

```python
# services/guard_riesgo/app.py — el agente escala, no decide solo
minimo = semaforo_minimo(ver, alerta)              # reglas: rojo si hay discrepancias duras, amarillo si hay dudas
semaforo = propuesto if NIVEL[propuesto] > NIVEL[minimo] else minimo   # la IA puede subirlo, nunca bajarlo
if semaforo == "rojo" and minimo != "rojo":        # sin una regla incumplida, la IA no puede rechazar
    semaforo = "amarillo"
```

El motivo de un rechazo automático siempre es el detalle de la regla incumplida, por ejemplo: «El comprobante indica 850.00 y la operación es por 1,000.00». Así el cliente y el auditor reciben un motivo verificable.

### 2.3 Catálogo de APIs nuevas

**URL base:** la misma del parcial (`ApiUrl`). Formato JSON y errores `{mensaje, codigo}`.

| Método | Ruta | Acceso | Códigos de respuesta |
|---|---|---|---|
| GET | `/validaciones/{id_operacion}` | JWT (dueño) | 200 · 401 · 404 |
| GET | `/validaciones/{id_operacion}/admin` | x-admin-key | 200 · 403 · 404 |
| GET | `/validaciones/admin?estado=en_revision` | x-admin-key | 200 · 400 · 403 |
| POST | `/validaciones/{id_operacion}/decision` | x-admin-key | 202 · 400 · 403 · 409 (no espera revisión o ya decidida) · 410 (revisión vencida) · 502 |
| POST | `/operaciones/{id}/comprobante` *(modificada)* | JWT | Igual que en el parcial; además inicia NexoGuard |

```jsonc
// GET /validaciones/NX-XXXXXXXX  (vista del cliente)
{ "id_operacion": "NX-XXXXXXXX", "estado": "finalizada", "fecha_inicio": "…", "fecha_fin": "…",
  "estado_final": "Rechazada", "decidido_por": "agente",
  "motivo": "El comprobante indica 850.00 y la operación es por 1,000.00." }

// POST /validaciones/NX-XXXXXXXX/decision   (cabecera x-admin-key)
{ "decision": "rechazar", "motivo": "El comprobante fue alterado." }
// → 202 { "mensaje": "Decisión registrada. La operación se actualizará en unos segundos.", … }
```

### 2.4 Base de datos `nexo-validaciones`

PK `id_operacion`, SK `fecha_inicio`, con dos GSI: `numero-operacion-index` (disperso, KEYS_ONLY) para los duplicados y `estado-fecha-index` para la cola de revisión. El `task_token` se elimina en cuanto se decide y ninguna ruta lo devuelve; hay una prueba que lo verifica. Si dos operadores deciden al mismo tiempo, la eliminación condicional del token garantiza que solo una decisión cuente.

**[PENDIENTE: captura de la tabla `nexo-validaciones` en la consola de DynamoDB con los 4 escenarios.]**

## 3. Pruebas

### 3.1 Pruebas automatizadas

| Suite | Resultado | Qué cubre de NexoGuard |
|---|---|---|
| Backend: `python -m pytest` | **74 aprobadas** (57 del parcial + 17 nuevas) | Reglas (monto, moneda, cuenta/CCI de NexoCambio, duplicado, fecha, lectura no confiable), barreras del agente de riesgo, normalización del extractor y PDF, API Validaciones (cola, decisión, 400/403/409, token oculto, aislamiento entre clientes), `StartExecution` y `aplicar_decision` en Operaciones, tolerancia a fallos de Step Functions |
| Frontend: `npx ng test` | **65 aprobadas** (5 nuevas) | Pantalla final con validación en vivo, cola NexoGuard, decisión por la API Validaciones, motivo sugerido, bloqueo mientras se valida |

Groq y Step Functions se simulan en estas pruebas; no necesitan credenciales ni internet.

### 3.2 Validación de los agentes con Groq real (31-oct-2026)

| Comprobante ficticio | Lo que extrajo el Agente Extractor | Resultado esperado del workflow |
|---|---|---|
| 01 BCP S/ 1,000.00 | Monto, moneda, N° 04417382, destino NexoCambio · 0-39 (confianza 0.95) | 🟢 Aprobación automática |
| 02 Interbank S/ 250.00 | Destino CCI ****0039-14 (banco de origen no leído: regla solo informativa) | 🟢 Aprobación automática |
| 03 S/ 850.00 | Monto 850.00 | 🔴 Rechazo: monto distinto |
| 04 Cuenta ajena | Destinatario «Inversiones Andinas E.I.R.L.» · Scotiabank | 🔴 Rechazo: cuenta que no es de NexoCambio |
| 05 Duplicado del 01 | N° 04417382 | 🔴 Rechazo: número ya usado |
| 06 US$ 12,000.00 | Monto y moneda USD | 🟡 Revisión + alerta de cumplimiento |
| 07 Borroso | `legible: false`, confianza 0.35 | 🟡 Revisión: lectura no concluyente |
| 08 Ticket de cafetería | `es_comprobante: false` | 🟡 Revisión: no es un comprobante |

Agente de Riesgo (`gpt-oss-20b`): con el comprobante 01 devolvió verde y la justificación «el monto de 1,000 PEN coincide con el de la operación…». Con el 03 devolvió rojo y su justificación citó «850.00 PEN, mientras la operación requiere 1,000.00 PEN». Tiempos: ~4.5 s por imagen y ~1.5–4 s por evaluación de riesgo.

### 3.3 Evidencia de uso desde Postman

La colección `postman/NexoCambio.postman_collection.json` incluye la carpeta **«6. NexoGuard»** (30 requests con pruebas automáticas):

| Escenario | Verificaciones |
|---|---|
| 6.1 Aprobación automática | Resultado «En proceso», `decidido_por = agente`, hito del historial con `actor = agente` |
| 6.2 Rechazo por monto distinto | «Rechazada» y motivo que cita 850 |
| 6.3 Rechazo por duplicado | «Rechazada» y motivo «ya se usó» |
| 6.4 Revisión humana | Cola de revisión, semáforo amarillo, alerta de cumplimiento, errores 403/400/409, aprobación del operador → «En proceso» con `actor = operador` |
| 6.5 Errores | 401 sin token, 404 sin validación, 403 sin clave |

Antes de cada corrida se ejecuta `python postman/generar_nexoguard.py`, que regenera los comprobantes con la fecha de hoy y números de operación nuevos, para que la corrida no choque con la detección de duplicados. La espera del resultado usa el Collection Runner.

**[PENDIENTE: captura del Collection Runner con las carpetas 2 y 6 en verde contra la API de AWS.]**

## 4. FrontEnd conectado a las APIs y al workflow

| Pantalla | Cambio | Archivo |
|---|---|---|
| Nueva operación, paso final | Tarjeta «Validando tu comprobante…» con 3 pasos animados; consulta `GET /validaciones/{id}` cada 3 s y muestra aprobado, en revisión o rechazado con motivo | `shared/components/estado-nexoguard/*`, `features/operar/*` |
| Detalle de operación (cliente) | La misma tarjeta, más el hito «Validado automáticamente por NexoGuard» o «Revisado por un especialista» | `features/operaciones/detalle/*` |
| Back-office: cola | Filtro «En revisión · NexoGuard» con semáforo, monto, alerta y motivo; oculta las operaciones ya resueltas a mano | `features/admin/admin-lista/*` |
| Back-office: detalle | Panel «Análisis NexoGuard»: semáforo, justificación, tabla «Declarado vs. Leído por el agente» (✓/✗), verificaciones, confianza y modelos. Aprobar/Rechazar llama a la API Validaciones (motivo prellenado) y no al PATCH | `features/admin/admin-detalle/*` |

**[PENDIENTE: capturas en la web desplegada: (1) validación en vivo, (2) resultado aprobado, (3) resultado rechazado con motivo, (4) cola NexoGuard, (5) revisión asistida, (6) versión móvil.]**

## 5. Despliegue en AWS Academy

```bash
# 1. Iniciar el Learner Lab y copiar las credenciales en ~/.aws/credentials
# 2. Desde la raíz del repositorio (rama nexoguard):
ALERT_EMAIL=frank.laura@utec.edu.pe ./scripts/deploy.sh
# 3. Confirmar en el correo la suscripción al tema SNS «nexo-dev-nexoguard»
```

`deploy.sh` empaqueta las Lambdas, la capa y la definición del workflow; despliega el stack `nexocambio-dev` (lee la clave de Groq de `.secrets/groq_api_key`); compila el frontend y lo publica en S3.

| Recurso | Valor |
|---|---|
| Sitio web (HTTPS) | **[PENDIENTE: salida SitioWebHttpsUrl]** |
| API base | **[PENDIENTE: salida ApiUrl]** |
| Workflow | **[PENDIENTE: salida MaquinaNexoGuard]** |
| Región | us-east-1 |

**[PENDIENTE: captura de los recursos del stack en CloudFormation y del correo de NexoGuard recibido.]**

## 6. Repositorio

- Código fuente: **https://github.com/frankcg/nexocambio** (rama `nexoguard`; fusionar a `main` antes de la entrega y verificar que el repositorio sea público).
- Estructura nueva: `services/{validaciones,guard_extraer,guard_verificar,guard_riesgo}`, `statemachine/`, `layer/python/nexo_groq.py`, `docs/final/`, `postman/generar_nexoguard.py`.
- La clave de Groq no está en el repositorio: `.secrets/` está en `.gitignore`.

## 7. Limitaciones conocidas y trabajo futuro

| Limitación | Motivo | Mejora propuesta |
|---|---|---|
| Comprobantes PDF van a revisión humana | La Lambda no incluye una librería para convertir PDF a imagen (sin dependencias empaquetadas) | Capa con PyMuPDF o Amazon Textract |
| ~3 comprobantes por minuto | Límite de la capa gratuita de Groq | Plan de pago de Groq o cola SQS con control de concurrencia |
| `qwen3.8-27b` está en *Preview* en Groq | Es el único modelo de visión disponible en la cuenta | El modelo es un parámetro del template: se cambia sin tocar código |
| Correo solo al back-office y a cumplimiento | Amazon SES restringido en AWS Academy | SES con dominio verificado (HU18) |
| Cuentas de NexoCambio duplicadas en el front y en `guard-verificar` | Simplificación del MVP | Servicio de configuración único (Parameter Store) |
| Detección de duplicados por N° de operación | Suficiente para el MVP | Agregar el hash del archivo (detecta la misma imagen reenviada) |

## 8. Guion sugerido para la exposición (10 min)

| Min. | Tema | Parte | Responsable |
|---|---|---|---|
| 1 | Problema de NexoCambio y nivel elegido (Nivel 4) | A | [Integrante] |
| 1 | Benchmark y por qué AWS | A | [Integrante] |
| 1 | Historias de usuario y MVP | A | [Integrante] |
| 2 | Arquitectura, workflow y barreras «la IA lee, las reglas deciden» | B | [Integrante] |
| 1 | Costos (el 90% es IA) y región | B | [Integrante] |
| 3 | **Demo en vivo:** comprobante correcto (grafo verde), monto distinto (rechazo) y monto alto (cola, revisión asistida, aprobación y correo) | C | [Integrante] |
| 1 | Postman, pruebas y repositorio | C | [Integrante] |

Recomendaciones para la demo:

- Iniciar el lab 15 minutos antes.
- Regenerar los comprobantes (`python scripts/generar_comprobantes.py`) y la colección.
- Ejecutar un caso de prueba previo, para que las Lambdas no arranquen en frío durante la exposición.
- Procesar los casos de uno en uno, para no topar el límite de Groq.

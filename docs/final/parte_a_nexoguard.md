# PARTE A — ANÁLISIS (QUÉ)

> Proyecto Final · Cloud Computing (CDIA V5) · UTEC Posgrado
> Nivel elegido: **Nivel 4 — Workflow Agéntico de Autonomía Moderada** (AWS Step Functions + API Groq sin memoria).

## 1. Nombre del Workflow Agéntico

**NexoGuard — Validación inteligente de operaciones de cambio**

| Campo | Detalle |
|---|---|
| Empresa | NexoCambio — startup fintech ficticia, casa de cambio de divisas y criptoactivos 100% digital (desplegada en AWS en el Proyecto Parcial). |
| Problemática | Hoy cada comprobante de transferencia lo revisa **manualmente** un operador de back-office: abre la imagen, compara monto, banco, cuenta de destino y titular contra la operación, y decide. Es lento (el cliente espera), no escala con el volumen, depende del criterio de cada operador y no deja registrado *por qué* se aprobó o rechazó. Además, los comprobantes falsos, alterados o reutilizados son un fraude frecuente en casas de cambio digitales del Perú. |
| Solución | Un workflow agéntico que, al adjuntar el comprobante, **extrae sus datos con IA, los contrasta con la operación, evalúa el riesgo y decide la ruta**: aprobar automáticamente, enviar a revisión humana asistida o rechazar con motivo. Notifica el resultado y deja trazabilidad completa. |
| Nivel de autonomía | **Nivel 4:** los agentes siguen una ruta predefinida (Step Functions), consultan APIs (Groq, Operaciones, Validaciones), toman decisiones lógicas intermedias (coincidencia y semáforo de riesgo) y notifican resultados. Los casos dudosos siempre pasan por un humano. |
| Relación con el parcial | Implementa lo que el Proyecto Parcial dejó **fuera del MVP**: score/semáforo de riesgo, automatización regulatoria y notificaciones por correo. |

## 2. Benchmark de stacks tecnológicos para implementar el workflow

Se evaluaron tres stacks distintos de AWS con los que podría construirse NexoGuard, y AWS como cuarta alternativa. En todos los casos el workflow es el mismo: recibir el comprobante → extraer datos con un LLM con visión → validar contra la operación → evaluar riesgo → decidir ruta (con posible aprobación humana) → guardar → notificar.

| Alternativa | Orquestación | IA / LLM | Cómputo y datos | Aprobación humana |
|---|---|---|---|---|
| **1. n8n** (open source, low-code) | Editor visual de nodos; self-hosted (Docker) o n8n Cloud | Nodos *AI Agent* / LLM (OpenAI, Gemini, Groq, etc.) | Nodos de código JS/Python; BD externa (PostgreSQL, Supabase) | Nodo *Wait* + formulario o webhook |
| **2. Microsoft Azure** | Azure Logic Apps (Consumption) o Durable Functions | Azure OpenAI (GPT-4o con visión) | Azure Functions + Cosmos DB + Blob Storage | Conector de aprobación por correo / Durable Functions *external events* |
| **3. Google Cloud** | Cloud Workflows | Vertex AI (Gemini, multimodal) | Cloud Run Functions + Firestore + Cloud Storage | *Callbacks* de Cloud Workflows |
| **4. AWS** ✔ | AWS Step Functions (Standard) | API Groq (Llama multimodal) — Bedrock no está habilitado en AWS Academy | AWS Lambda + DynamoDB + S3; SNS para correo | Patrón `waitForTaskToken` |

### Cuadro comparativo

| Criterio | n8n | Azure | Google Cloud | **AWS** |
|---|---|---|---|---|
| Modelo de despliegue | Servidor propio (no serverless) o SaaS | Serverless | Serverless | **Serverless** |
| Diseño visual del flujo | Muy bueno (nativo) | Bueno (diseñador de Logic Apps) | Limitado (YAML, sin editor visual) | **Bueno** (Workflow Studio + grafo de ejecución en vivo) |
| Integración con LLM | Nativa, muchos proveedores | Nativa con Azure OpenAI | Nativa con Gemini | Vía Lambda (cualquier API, p. ej. Groq) |
| Aprobación humana (*human-in-the-loop*) | Sí | Sí | Sí | **Sí, nativa** (`waitForTaskToken`, hasta 1 año de espera) |
| Manejo de errores y reintentos | Básico por nodo | Bueno | Bueno | **Muy bueno** (`Retry`/`Catch` declarativos por estado) |
| Trazabilidad / auditoría | Historial de ejecuciones | Run history | Logs de ejecución | **Historial visual de cada ejecución** + CloudWatch |
| Modelo de costo | Licencia/servidor fijo mensual | Pago por acción | Pago por paso | **Pago por transición de estado** (capa gratuita mensual) |
| Curva de aprendizaje | Baja | Media | Media | Media |
| Encaje con NexoCambio | Requiere integrar con AWS desde fuera | Requiere migrar o integrar entre nubes | Requiere migrar o integrar entre nubes | **Total**: operaciones, comprobantes (S3) y APIs ya están en AWS |
| Disponible para el equipo | Requiere instalar o pagar | Requiere suscripción | Requiere cuenta con facturación | **AWS Academy Learner Lab** |

> Nota: los modelos de precios y funcionalidades corresponden a la documentación oficial de cada proveedor y pueden cambiar; se recomienda verificarlos antes de la entrega.

**Conclusión del benchmark.** n8n es el más rápido para prototipar, pero no es serverless y obliga a operar un servidor o pagar una licencia. Azure y Google Cloud ofrecen capacidades equivalentes, pero implicarían mover o duplicar datos que ya viven en AWS. **AWS Step Functions** es la mejor opción para NexoGuard: se integra de forma nativa con la plataforma existente, ofrece aprobación humana nativa, reintentos declarativos, trazabilidad visual de cada decisión y pago por uso. Groq aporta inferencia de LLM muy rápida y de bajo costo, y sustituye a Amazon Bedrock, que no está disponible en AWS Academy.

## 3. ¿Qué tendrá el Workflow Agéntico?

### 3.1 Tipos de clientes y usuarios

| Tipo de usuario | Descripción | Qué hace en NexoGuard |
|---|---|---|
| Cliente persona natural | Persona registrada que cambia divisas o cripto. | Adjunta su comprobante y ve en la web cómo su operación se valida automáticamente, con el resultado y el motivo si es rechazada. |
| Cliente empresa | Empresa registrada con RUC mediante un representante. Suele operar montos altos. | Lo mismo que la persona natural; sus montos altos activan con más frecuencia la revisión humana. |
| Operador de back-office | Personal interno que valida transferencias. | Ya no revisa todo: solo atiende los casos en **revisión** (🟡), con el análisis del agente a la vista (datos extraídos, discrepancias, semáforo y justificación), y aprueba o rechaza. |
| Oficial de cumplimiento | Responsable de prevención de lavado de activos (la casa de cambio es sujeto obligado ante la UIF-Perú). | Recibe por correo las alertas de operaciones de riesgo alto o de montos iguales o mayores al umbral de registro (referencial: US$ 10,000). |
| Agentes de IA (actores del sistema) | No son usuarios, pero ejecutan tareas dentro del flujo. | **Agente Extractor**: lee el comprobante. **Agente de Riesgo**: asigna el semáforo y explica por qué. |

### 3.2 Funcionalidades

| Módulo | Funcionalidad | Alcance |
|---|---|---|
| Disparo del workflow | Al adjuntar el comprobante se inicia automáticamente una ejecución de Step Functions; el cliente ve el estado «Validando automáticamente». | MVP (HU10) |
| Agente Extractor | Groq con visión lee el comprobante y devuelve JSON: banco, monto, moneda, fecha, N° de operación, cuenta de destino, titular. | MVP (HU11) |
| Validación de coincidencia | Reglas deterministas: monto, moneda, cuenta de destino de NexoCambio, banco de origen, antigüedad de la fecha y **N° de operación no reutilizado**. | MVP (HU12) |
| Agente de Riesgo | Groq asigna un semáforo 🟢🟡🔴 con justificación en lenguaje natural, a partir de la validación, el monto y el perfil de la operación. | MVP (HU13) |
| Decisión por ruta | 🟢 y todo coincide → pasa a «En proceso» sin intervención. 🟡 → revisión humana. 🔴 → «Rechazada» con motivo generado. | MVP (HU14) |
| Revisión humana asistida | El back-office ve el análisis del agente y decide; su decisión reanuda el workflow (`waitForTaskToken`). | MVP (HU15) |
| Notificaciones | Correo (Amazon SNS) al operador y al oficial de cumplimiento con el resultado y las alertas. | MVP (HU16) |
| API Validaciones | API propia con su tabla DynamoDB `nexo-validaciones`: guarda y expone cada análisis (auditoría). | MVP (HU17) |
| Correo al cliente | Avisar al cliente por correo del resultado de su operación (requiere Amazon SES con dominio verificado). | Post-MVP (HU18) |
| Panel de métricas | Porcentaje de aprobación automática, tiempo medio de validación, motivos de rechazo más frecuentes. | Post-MVP (HU19) |

### 3.3 Historias de usuario y criterios de aceptación (Gherkin — BDD)

Se numeran a partir de HU10 para mantener la continuidad con las HU1–HU9 del Proyecto Parcial.

---

**Historia de Usuario 10: Validación automática al adjuntar el comprobante** — `MVP`

> **COMO** cliente,
> **QUIERO** que mi comprobante se valide automáticamente al adjuntarlo,
> **PARA** que mi operación avance sin esperar la revisión manual de un operador.

```gherkin
GIVEN el cliente tiene una operación en estado «Pendiente de comprobante»
WHEN adjunta una imagen o PDF válido como comprobante
AND selecciona Confirmar operación
THEN se inicia una ejecución del workflow NexoGuard para esa operación
AND la operación muestra el estado «Validando automáticamente»
AND el cliente ve un mensaje indicando que recibirá el resultado en unos minutos

GIVEN la validación automática terminó
WHEN el cliente abre el detalle de su operación
THEN ve el nuevo estado («En proceso», «En revisión» o «Rechazada»)
AND si fue rechazada, ve el motivo en lenguaje claro
AND el historial registra que la decisión la tomó la validación automática o un operador
```

---

**Historia de Usuario 11: Extracción de datos del comprobante con IA** — `MVP`

> **COMO** operador de back-office,
> **QUIERO** que un agente lea el comprobante y extraiga sus datos,
> **PARA** no tener que transcribirlos ni compararlos a ojo.

```gherkin
GIVEN se inició el workflow con un comprobante legible
WHEN el Agente Extractor procesa la imagen
THEN obtiene banco de origen, monto, moneda, fecha, número de operación, cuenta de destino y titular
AND devuelve los datos en formato JSON con un nivel de confianza
AND los datos quedan guardados en la API Validaciones

GIVEN el comprobante está borroso, incompleto o no es un comprobante bancario
WHEN el Agente Extractor no puede obtener los campos obligatorios
THEN marca la extracción como «no concluyente»
AND la operación se envía a revisión humana con el motivo «Comprobante ilegible o no reconocido»

GIVEN la API Groq no responde o devuelve un error
WHEN se agotan los reintentos configurados
THEN la operación se envía a revisión humana
AND no se pierde la operación ni el comprobante
```

---

**Historia de Usuario 12: Verificación de coincidencia con la operación** — `MVP`

> **COMO** operador de back-office,
> **QUIERO** que el sistema compare los datos del comprobante con la operación registrada,
> **PARA** detectar discrepancias y fraudes antes de enviar dinero.

```gherkin
GIVEN se extrajeron los datos del comprobante
WHEN se comparan con la operación registrada
THEN se verifica que el monto y la moneda coincidan con el monto de origen de la operación
AND que la cuenta de destino sea una cuenta de NexoCambio para esa moneda
AND que la fecha del comprobante no sea anterior a la creación de la operación
AND que el número de operación no haya sido usado en otra operación
AND el resultado lista cada verificación como «cumple» o «no cumple»

GIVEN el número de operación del comprobante ya fue usado en otra operación
WHEN se ejecuta la verificación
THEN la verificación de duplicado queda como «no cumple»
AND se registra la operación previa con la que coincide
```

---

**Historia de Usuario 13: Semáforo de riesgo con justificación** — `MVP`

> **COMO** oficial de cumplimiento,
> **QUIERO** que cada operación reciba un nivel de riesgo explicado,
> **PARA** concentrar la atención en las operaciones sospechosas.

```gherkin
GIVEN la verificación de coincidencia terminó
WHEN el Agente de Riesgo evalúa la operación
THEN asigna un semáforo: Verde (bajo), Amarillo (medio) o Rojo (alto)
AND redacta una justificación breve en español que cita los hechos evaluados

GIVEN todas las verificaciones cumplen
AND el monto es menor al umbral de revisión
WHEN el Agente de Riesgo evalúa la operación
THEN el semáforo es Verde

GIVEN el monto es igual o mayor al umbral de registro (referencial: US$ 10,000)
WHEN el Agente de Riesgo evalúa la operación
THEN el semáforo es al menos Amarillo
AND se marca la operación para el oficial de cumplimiento
```

---

**Historia de Usuario 14: Decisión automática según la ruta** — `MVP`

> **COMO** gerente de operaciones de NexoCambio,
> **QUIERO** que el workflow decida automáticamente los casos claros,
> **PARA** reducir el tiempo de atención y la carga del back-office.

```gherkin
GIVEN el semáforo es Verde y todas las verificaciones cumplen
WHEN el workflow evalúa la ruta
THEN la operación pasa automáticamente a «En proceso»
AND el historial registra «Aprobada por validación automática»

GIVEN el semáforo es Rojo por un indicio claro de fraude (cuenta de destino ajena o comprobante duplicado)
WHEN el workflow evalúa la ruta
THEN la operación pasa a «Rechazada»
AND el motivo de rechazo describe la discrepancia encontrada

GIVEN el monto o la moneda del comprobante no coinciden con la operación
WHEN el workflow evalúa la ruta
THEN el semáforo es Amarillo y la operación va a revisión humana (puede ser un error de tipeo o un pago parcial)
AND el operador ve la discrepancia con el motivo de rechazo sugerido

GIVEN el semáforo es Amarillo
WHEN el workflow evalúa la ruta
THEN la operación pasa a «En revisión»
AND el workflow queda en espera de la decisión de un operador
```

---

**Historia de Usuario 15: Revisión humana asistida por el agente** — `MVP`

> **COMO** operador de back-office,
> **QUIERO** ver el análisis del agente y decidir sobre las operaciones en revisión,
> **PARA** resolver los casos dudosos rápido y con toda la información.

```gherkin
GIVEN el operador ingresó al back-office con su clave
WHEN filtra la cola por «En revisión»
THEN ve solo las operaciones que el workflow envió a revisión
AND cada una muestra su semáforo

GIVEN el operador abre una operación «En revisión»
WHEN revisa el detalle
THEN ve el comprobante junto a los datos extraídos por el agente
AND ve la lista de verificaciones con «cumple» o «no cumple»
AND ve la justificación del semáforo

GIVEN el operador decide Aprobar o Rechazar (con motivo)
WHEN confirma su decisión
THEN el workflow se reanuda y termina con esa decisión
AND la operación pasa a «En proceso» o «Rechazada»
AND el historial registra que la decisión fue de un operador
```

---

**Historia de Usuario 16: Notificación del resultado por correo** — `MVP`

> **COMO** operador de back-office u oficial de cumplimiento,
> **QUIERO** recibir un correo cuando el workflow requiera mi atención o detecte riesgo alto,
> **PARA** actuar a tiempo sin estar mirando la pantalla.

```gherkin
GIVEN una operación pasa a «En revisión»
WHEN el workflow llega al paso de notificación
THEN se envía un correo con el código de operación, el monto, el semáforo y el enlace al back-office

GIVEN una operación tiene semáforo Rojo o supera el umbral de registro
WHEN el workflow llega al paso de notificación
THEN el oficial de cumplimiento recibe un correo de alerta con la justificación del agente

GIVEN el envío del correo falla
WHEN se agotan los reintentos
THEN la decisión sobre la operación se mantiene
AND el fallo queda registrado en CloudWatch
```

---

**Historia de Usuario 17: Registro auditable de cada validación** — `MVP`

> **COMO** oficial de cumplimiento,
> **QUIERO** consultar el análisis completo de cada validación,
> **PARA** poder explicar ante un auditor por qué se aprobó o rechazó una operación.

```gherkin
GIVEN una operación pasó por el workflow
WHEN se consulta la API Validaciones con el ID de la operación
THEN devuelve los datos extraídos, las verificaciones, el semáforo, la justificación, la ruta tomada, quién decidió y las fechas de cada paso

GIVEN se consulta una operación que no tiene validación registrada
WHEN se llama a la API Validaciones
THEN responde 404 con el mensaje «La operación no tiene validaciones registradas»
```

---

**Historia de Usuario 18: Correo de resultado al cliente** — `POST-MVP`

> **COMO** cliente,
> **QUIERO** recibir un correo cuando cambie el estado de mi operación,
> **PARA** enterarme sin entrar a la plataforma.

```gherkin
GIVEN la operación del cliente cambia a «En proceso» o «Rechazada»
WHEN el workflow termina
THEN el cliente recibe un correo en la dirección registrada con el nuevo estado y el motivo si corresponde
```

---

**Historia de Usuario 19: Panel de métricas de validación** — `POST-MVP`

> **COMO** gerente de operaciones,
> **QUIERO** ver indicadores del workflow,
> **PARA** medir cuánto trabajo manual se ahorra.

```gherkin
GIVEN existen validaciones registradas
WHEN el gerente abre el panel de métricas
THEN ve el porcentaje de aprobaciones automáticas, revisiones y rechazos
AND el tiempo medio de validación
AND los motivos de rechazo más frecuentes
```

### 3.4 Propuesta de valor

**NexoGuard convierte la validación de comprobantes de un cuello de botella manual en un proceso de minutos, más seguro y auditable.**

- **Para el cliente — rapidez:** su operación pasa de esperar a un operador (minutos u horas, según la carga) a validarse en segundos cuando todo cumple.
- **Para el back-office — foco:** el operador solo atiende los casos dudosos, y lo hace con el análisis del agente a la vista en lugar de empezar de cero.
- **Para la empresa — antifraude:** detecta montos que no coinciden, transferencias a cuentas ajenas y comprobantes reutilizados antes de enviar el dinero.
- **Para cumplimiento — trazabilidad:** cada decisión queda registrada con sus datos, verificaciones, semáforo y una justificación en lenguaje natural, y quién tomó la decisión final (agente u operador).
- **Control humano donde importa:** el agente decide solo los casos claros; los casos ambiguos o de riesgo siempre pasan por una persona.
- **Bajo costo:** serverless y pago por uso, sin servidores encendidos, sobre la misma infraestructura de NexoCambio.

### 3.5 Selección del MVP

**Criterio de selección.** Se prioriza el flujo agéntico completo de punta a punta, demostrable en AWS con las tres rutas posibles: cliente adjunta comprobante → extracción con IA → verificación → semáforo → decisión (automática o humana) → registro → notificación → el cliente ve el resultado. Quedan fuera las funciones que requieren servicios restringidos en AWS Academy (SES con dominio verificado) o que no son necesarias para demostrar el workflow (panel de métricas).

| ID | Historia | Clasificación | Cómo se comprueba |
|---|---|---|---|
| HU10 | Validación automática al adjuntar | MVP | `POST /operaciones/{id}/comprobante` inicia la ejecución (`StartExecution`); visible en la consola de Step Functions |
| HU11 | Extracción con IA | MVP | Estado `ExtraerComprobante` (Lambda + Groq visión); salida JSON en el historial de ejecución |
| HU12 | Verificación de coincidencia | MVP | Estado `ValidarCoincidencia` (Lambda); lista de verificaciones |
| HU13 | Semáforo de riesgo | MVP | Estado `EvaluarRiesgo` (Lambda + Groq texto) |
| HU14 | Decisión por ruta | MVP | Estado `Choice` → `AprobarAutomatico` / `EsperarRevision` / `RechazarAutomatico` |
| HU15 | Revisión humana asistida | MVP | `POST /validaciones/{id_operacion}/decision` (x-admin-key) → `SendTaskSuccess` |
| HU16 | Notificación por correo | MVP | Estado `Notificar` → tema SNS con suscripción de correo |
| HU17 | Registro auditable | MVP | `GET /validaciones/{id_operacion}` (API Validaciones + tabla `nexo-validaciones`) |
| HU18 | Correo al cliente | Post-MVP | — |
| HU19 | Panel de métricas | Post-MVP | — |

**Flujo que debe funcionar al término del MVP:** el cliente adjunta su comprobante y el workflow NexoGuard se ejecuta. En los tres casos de demostración: (1) un comprobante correcto se aprueba automáticamente, (2) un monto alto, un monto distinto o un comprobante poco legible va a revisión, el operador lo resuelve desde el back-office y el workflow termina, y (3) un comprobante enviado a una cuenta ajena o duplicado se rechaza automáticamente con motivo. En todos los casos se envía el correo correspondiente y la validación queda consultable en la API Validaciones.

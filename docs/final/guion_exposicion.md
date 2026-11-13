# Guion de la exposición final de NexoGuard (20 min, 5 integrantes)

Diapositivas: deck «NexoGuard — Exposición final» (cada diapositiva lleva en sus notas el texto de quien la expone).
Demo web: `docs/final/guion_demo.md`. Preparación del entorno: README, «Exposición».

| Parte | Expone | Tiempo | Diapositivas |
|---|---|---|---|
| 1. Problema, solución y benchmark | [Integrante 1] | 0:00 – 4:00 | 1 a 5 |
| 2. Usuarios, MVP y propuesta de valor | [Integrante 2] | 4:00 – 8:00 | 6 a 8 |
| 3. Arquitectura, workflow, reglas y agentes | [Integrante 3] | 8:00 – 12:00 | 9 a 12 |
| 4. Demo en vivo (verde, rojo, amarillo) | [Integrante 4] | 12:00 – 16:00 | 13 y 14 (respaldo) |
| 5. Pruebas, costos, límites y cierre | [Integrante 5] | 16:00 – 20:00 | 15 a 18 |

## Antes de empezar (todo el equipo, 30 min antes)

1. [Integrante 4] inicia el Learner Lab, actualiza `~/.aws/credentials` y ejecuta
   `python scripts/preparar_exposicion.py --ensayo`. Debe terminar con «Listo para exponer».
2. Después de eso **nadie** usa «Reiniciar datos de prueba» ni la 6.0 de Postman: borran los depósitos del banco
   y el caso verde iría a revisión.
3. Pestañas abiertas en la laptop de la demo: web como cliente (`demo@nexocambio.pe` / `Demo1234`), back-office
   (`#/admin`), consola de Step Functions (`nexo-dev-nexoguard`) y el correo suscrito al tema SNS.
4. Ensayar el cronómetro: cada integrante tiene 4 minutos. Si alguien se pasa, el siguiente recorta, nunca la demo.

---

## Parte 1 · [Integrante 1] · 0:00 – 4:00

**Objetivo:** que se entienda el problema y por qué la solución es un workflow agéntico en AWS.

| Min. | Diapositiva | Qué decir |
|---|---|---|
| 0:00 | 1. Portada | Presentar al equipo y el proyecto: NexoGuard, un workflow agéntico de nivel 4 que valida los comprobantes de NexoCambio. |
| 0:20 | 2. Agenda | Cinco partes de cuatro minutos; nombrar a cada integrante y su tema. |
| 0:40 | 3. Problema | Hoy un operador revisa cada comprobante a mano: lento, no escala, inconsistente y sin rastro. Sumar el riesgo de fraude: comprobantes reutilizados o enviados a otra cuenta. |
| 1:30 | 4. Solución | El flujo: adjunta → extrae (IA) → verifica (reglas) → concilia con el banco → riesgo (IA) → decide. Tres salidas: verde, amarillo y rojo. Nivel 4: ruta predefinida y los dudosos siempre pasan por una persona. |
| 2:40 | 5. Benchmark | n8n no es serverless; Azure y Google obligan a mover datos. Step Functions: aprobación humana nativa (`waitForTaskToken`), Retry/Catch por estado y grafo visual como auditoría. Groq porque Bedrock no está en AWS Academy. |

**Transición:** «Ya vimos el qué; [Integrante 2] nos cuenta para quién y qué entra en el MVP».

**Preguntas probables:**
- *¿Por qué nivel 4 y no 5?* Porque la ruta está predefinida y los agentes no deciden solos los casos dudosos; un
  rechazo indebido a un cliente que pagó es muy costoso.
- *¿Por qué no Bedrock?* No está habilitado en AWS Academy; Groq se consume por HTTPS desde Lambda y el modelo es un
  parámetro del template.

## Parte 2 · [Integrante 2] · 4:00 – 8:00

**Objetivo:** mostrar a los usuarios, el alcance del MVP y el valor para cada uno.

| Min. | Diapositiva | Qué decir |
|---|---|---|
| 4:00 | 6. Usuarios | Cliente (persona o empresa), operador de back-office (solo los amarillos), oficial de cumplimiento (alertas por correo desde US$ 10,000, umbral UIF) y los dos agentes de IA. |
| 5:10 | 7. MVP | Historias HU10 a HU17 en Gherkin, todas implementadas: disparo automático, extracción, verificación, semáforo, ruta, revisión humana, correo y registro auditable. Fuera: correo al cliente (SES restringido) y panel de métricas. |
| 6:40 | 8. Propuesta de valor | Qué gana cada actor. El 75 % es un **supuesto** del estudio de costos: ~11,000 revisiones manuales menos al mes en el piloto. |

**Transición:** «¿Cómo está construido? Le paso la palabra a [Integrante 3]».

**Preguntas probables:**
- *¿Cómo se eligió el MVP?* Por el flujo completo de punta a punta, demostrable con las tres rutas; quedó fuera lo que
  depende de servicios restringidos en Academy o no hace falta para demostrar el workflow.
- *¿El 75 % está medido?* No: es el supuesto del escenario piloto del estudio de costos.

## Parte 3 · [Integrante 3] · 8:00 – 12:00

**Objetivo:** explicar la arquitectura, el workflow y la decisión clave: la IA no decide sola.

| Min. | Diapositiva | Qué decir |
|---|---|---|
| 8:00 | 9. Arquitectura | Serverless en us-east-1. Lo que ya existía (API Gateway, Lambdas, DynamoDB, S3) y lo nuevo (Step Functions, 4 Lambdas, API Validaciones, banco simulado, SNS). Cada microservicio con su base de datos. Todo en CloudFormation. |
| 9:00 | 10. Workflow | Ejecuciones reales. Conciliación con Wait (30 s, hasta 4 veces). Ruta amarilla en pausa con `waitForTaskToken`, sin costo, hasta 72 h. Retry/Catch: si Groq falla, va a revisión. |
| 10:00 | 11. Reglas | La IA lee y explica; las reglas deciden. Solo dos reglas rechazan (cuenta ajena y duplicado). Barreras: el agente sube el semáforo, nunca lo baja, y no rechaza sin una regla incumplida. |
| 11:10 | 12. Agentes | Extractor (`qwen3.8-27b`, visión) y Riesgo (`gpt-oss-20b`, texto), sin memoria, temperatura 0, JSON. Retry ante 429. Sin datos personales a la IA. |

**Transición:** «Ahora [Integrante 4] lo muestra funcionando en AWS».

**Preguntas probables:**
- *¿Qué pasa si Groq se cae?* El estado reintenta (20, 40 y 80 s) y, si sigue fallando, el Catch manda la operación a
  revisión humana: nunca se pierde.
- *¿Por qué Standard y no Express?* `waitForTaskToken` solo existe en Standard, y guarda el historial visual de cada
  ejecución.
- *¿Dónde está el token?* Se guarda en DynamoDB y nunca sale al navegador; el operador decide por la API.

## Parte 4 · [Integrante 4] · 12:00 – 16:00 (demo en vivo)

**Objetivo:** ver las tres rutas en la web, el back-office, Step Functions y el correo.

Datos fijos de los tres casos: Casa de Cambio, envía PEN 1,000, recibe USD en **Interbank · Ahorros ·
8983141592653**, N° de operación **vacío**. Esperar ~20 s entre casos (límite de Groq).

| Min. | Caso | Qué hacer y mostrar |
|---|---|---|
| 12:00 | Diapositiva 13 | Presentar los tres casos en 20 s y pasar al navegador. |
| 12:20 | 1 · Verde | Banco de origen **BCP**, subir `01_ok_bcp_pen_1000.png`. «Validando…» → «¡Comprobante validado!» (≈ 10 s) y el hito «Validado automáticamente por NexoGuard». Abrir la ejecución en Step Functions: camino en verde. |
| 13:30 | 2 · Rojo | Banco de origen **BBVA**, subir `04_rojo_cuenta_ajena.png`. Rechazada en ≈ 5 s con el motivo «El dinero se envió a Inversiones Andinas…, que no es una cuenta de NexoCambio». |
| 14:30 | 3 · Amarillo | Banco de origen **BCP**, subir `03_amarillo_monto_distinto.png`. Back-office → cola «En revisión · NexoGuard» → abrir: semáforo amarillo, «Leído S/ 850 ✗», el banco confirma S/ 850. Rechazar con el motivo prellenado. Mostrar el correo «[NexoGuard] Revisión requerida» y que la ejecución en pausa terminó. |
| 15:50 | Cierre | «La IA leyó, las reglas decidieron y una persona resolvió lo dudoso». |

**Plan B:** si falla la red, las credenciales o Groq, pasar a la diapositiva 14 (capturas reales) y narrarla.

**Transición:** «[Integrante 5] nos cuenta cómo lo probamos y cuánto cuesta».

**Preguntas probables:**
- *¿El banco es real?* Es una API simulada por HTTPS con su propia clave, que hace de sistema externo; en producción
  se conecta la API de un banco o un agregador.
- *¿Y si el depósito llega tarde?* El workflow espera y reintenta; si llega durante la espera, se aprueba solo
  (caso 9 del guion de la demo).

## Parte 5 · [Integrante 5] · 16:00 – 20:00

**Objetivo:** dar evidencia, costos y límites con honestidad, y cerrar.

| Min. | Diapositiva | Qué decir |
|---|---|---|
| 16:00 | 15. Pruebas | 94 pruebas de backend y 68 de frontend. En AWS con Groq real, 8 de 8 escenarios. La carpeta 6 de Postman pasó completa dos veces seguidas tras reiniciar. El borroso y el ticket terminaron en revisión. |
| 17:00 | 16. Costos | US$ 0.0036 por validación; 87 % del costo es Groq; piloto ≈ US$ 56/mes (AWS solo US$ 6.80). Región us-east-1 por el Learner Lab; en Perú, evaluar sa-east-1 y la Ley 29733. |
| 18:20 | 17. Límites | PDF a revisión, ~3 comprobantes por minuto, modelo en Preview, sin correo al cliente, duplicados por número, banco simulado; y la mejora de cada uno. |
| 19:20 | 18. Cierre | «La IA lee, las reglas deciden y las personas resuelven lo dudoso». Gracias y preguntas. |

**Preguntas probables:**
- *¿Cómo calcularon los costos?* Con `docs/final/costos_nexoguard.py`: precios de lista de us-east-1 y de Groq, y
  duraciones medidas en las pruebas en AWS.
- *¿Qué harían primero para producción?* Plan de pago de Groq o cola SQS, conversión de PDF y la API real del banco.

## Reparto de preguntas al final

Cada integrante responde las preguntas de su parte. Si nadie sabe la respuesta: «Lo revisamos y les respondemos»,
sin inventar cifras.

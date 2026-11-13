# Guion de la demo NexoGuard (web)

## Preparación (antes de la exposición)

1. Iniciar el Learner Lab y actualizar las credenciales en `~/.aws/credentials` (incluye `aws_session_token`).
2. Reiniciar los datos, generar los comprobantes del día y registrar sus depósitos en el banco simulado, todo con un
   comando (ver el README, «Exposición»):
   ```bash
   python scripts/preparar_exposicion.py --ensayo
   ```
   Los comprobantes quedan en `tests/fixtures/comprobantes/`. **Después no usar «Reiniciar datos de prueba»**: borra
   los depósitos del banco. Si hay que reiniciar, volver a ejecutar el script.
3. Entrar a la web como cliente: `demo@nexocambio.pe` / `Demo1234`.

## Datos fijos de todos los casos

- **Modalidad:** Casa de Cambio (divisas). Cripto no se valida automáticamente (ver nota al final).
- **Cuenta de destino del cliente** (dónde recibe):
  - si recibe **USD**: banco **Interbank** · **Ahorros** · N° **8983141592653**
  - si recibe **PEN**: banco **BCP** · **Corriente** · N° **19324587100391**
- **N° de operación (opcional):** dejarlo vacío, salvo en el caso 7.
- Esperar **~20 s entre casos** (límite de Groq: ~3 comprobantes por minuto).

## Casos

| # | Caso | Resultado esperado | Envías | Recibes | Banco de origen | Comprobante a subir | Qué mostrar |
|---|---|---|---|---|---|---|---|
| 1 | Transferencia correcta | 🟢 **Aprobada automáticamente** (≈10 s) | **PEN 1,000** | USD | **BCP** | `01_ok_bcp_pen_1000.png` | La tarjeta «Validando…» pasa a «¡Comprobante validado!»; en el detalle, el hito «Validado automáticamente por NexoGuard» |
| 2 | Interbancaria correcta | 🟢 **Aprobada automáticamente** | **PEN 250** | USD | **Interbank** | `02_ok_interbank_pen_250.png` | Igual que el 1, vía CCI |
| 3 | Transferencia a otra cuenta | 🔴 **Rechazada automáticamente** (≈5 s) | **PEN 1,000** | USD | **BBVA** | `04_rojo_cuenta_ajena.png` | Motivo: «El dinero se envió a Inversiones Andinas… no es una cuenta de NexoCambio» |
| 4 | Comprobante reutilizado | 🔴 **Rechazada automáticamente** | **PEN 1,000** | USD | **BCP** | `05_rojo_duplicado_de_01.png` | Motivo: «El número de operación … ya se usó en la operación NX-…». **Hacerlo después del caso 1** |
| 5 | Monto alto (UIF) | 🟡 **En revisión** → el operador **aprueba** | **USD 12,000** | PEN | **Scotiabank** | `06_amarillo_monto_alto_usd.png` | Back-office: semáforo amarillo, alerta de cumplimiento, depósito ✓ confirmado; aprobar → «En proceso». Llega correo a cumplimiento |
| 6 | Monto distinto | 🟡 **En revisión** → el operador **rechaza** | **PEN 1,000** | USD | **BCP** | `03_amarillo_monto_distinto.png` | Back-office: «Leído S/ 850 ✗»; el banco confirma que llegaron S/ 850; rechazar con el motivo prellenado |
| 7 | N° declarado distinto *(alternativa al caso 2: usa el mismo comprobante)* | 🟡 **En revisión** → el operador **aprueba** | **PEN 250** | USD | **Interbank** | `02_ok_interbank_pen_250.png` y en «N° de operación» escribir **11111111** | Back-office: «El cliente declaró 11111111, pero el comprobante indica …» |
| 8 | Comprobante sin depósito («falsificado») | 🟡 **En revisión** (≈2 min) → el operador **rechaza** | **PEN 1,000** | USD | **BCP** | `09_amarillo_sin_deposito.png` | En Step Functions, el ciclo ConciliarConBanco ↔ EsperarDeposito (4 consultas); back-office: «Depósito: ✗ No encontrado en el banco» |
| 9 | Depósito que llega tarde | 🟢 **Aprobada automáticamente** al llegar el depósito | **PEN 1,000** | USD | **Interbank** | `10_verde_deposito_tardio.png`; luego, **dentro de 2 min**, ejecutar el comando de abajo | La tarjeta sigue «Validando…» hasta que se registra el depósito; entonces se aprueba sola |
| 10 | Imagen borrosa | 🟡 **En revisión** | **PEN 500** | USD | **Interbank** | `07_amarillo_borroso.png` | Back-office: «Lectura no concluyente (confianza 0.35)» |
| 11 | No es un comprobante | 🟡 **En revisión** | **PEN 1,000** | USD | **BCP** | `08_amarillo_no_es_comprobante.png` (ticket de cafetería) | Back-office: «La imagen no parece un comprobante bancario» |

Comando del caso 9 (misma semilla que en la preparación):

```bash
python scripts/generar_comprobantes.py --semilla 101 --deposito-tardio https://ryipifjwef.execute-api.us-east-1.amazonaws.com/v1
```

## Paso final (back-office, para cualquier caso aprobado)

Operación «En proceso» → **«Marcar como Procesada»** (el operador confirma que envió el dinero). En el detalle del cliente, el tercer punto se actualiza solo en ~10 s.

## Demo corta sugerida (exposición de 3 min)

Casos **1** (verde), **3** (rojo) y **6** o **8** (amarillo → decisión del operador), mostrando en paralelo el grafo de Step Functions.

## Nota: cripto

Las operaciones de Cripto (p. ej. PEN → USDT) no tienen cuenta bancaria de destino: NexoGuard no puede conciliarlas con el banco y las envía a **revisión manual**. Quedan fuera de la validación automática del MVP.

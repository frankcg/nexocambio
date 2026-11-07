#!/usr/bin/env python3
"""Costo mensual INCREMENTAL de NexoGuard (us-east-1) sobre la base de NexoCambio (docs/costos.json).
Precios de REFERENCIA: AWS (lista pública) y Groq (console.groq.com/docs/models, oct-2026).
Validar en https://calculator.aws antes de entregar. Uso: python docs/final/costos_nexoguard.py"""
import json
from pathlib import Path

P = dict(sfn_transicion=0.025 / 1000, sfn_gratis=4000, lambda_req=0.20 / 1e6, lambda_gbs=0.0000166667,
         apigw_http=1.00 / 1e6, ddb_wru=0.625 / 1e6, ddb_rru=0.125 / 1e6,
         sns_email=2.00 / 100_000, sns_email_gratis=1000, cw_alarm=0.10, cw_ingest_gb=0.50,
         groq_qwen_in=0.80 / 1e6, groq_qwen_out=4.00 / 1e6, groq_oss_in=0.075 / 1e6, groq_oss_out=0.30 / 1e6)

CONSULTAS_BANCO = 1.3       # consultas al banco por validación: la mayoría lo encuentra a la 1.ª; algunas esperan (Wait)
# Lambdas por validación: (invocaciones, memoria MB, duración ms) — duraciones medidas en las pruebas en AWS
LAMBDAS = {"guard-extraer": (1, 256, 5000), "guard-verificar": (1, 256, 300), "guard-riesgo": (1, 256, 2500),
           "guard-conciliar": (CONSULTAS_BANCO, 256, 400), "banco-simulado (consulta + depósito)": (CONSULTAS_BANCO + 1, 256, 150),
           "validaciones (iniciar/guardar)": (2, 256, 200), "operaciones (aplicar_decision)": (1, 512, 300)}
# ruta típica: 10 + 4 de la conciliación (Preparar, ¿Consultar?, Conciliar, ¿Encontrado?) + 3 por cada reintento
# (Wait, Conciliar, ¿Encontrado?); la de revisión suma 2 (NotificarRevision + EsperarRevision)
TRANSICIONES = 10 + 4 + 3 * (CONSULTAS_BANCO - 1)
FRAC_REVISION = 0.25         # 🟡 van a revisión humana
FRAC_ALERTA = 0.10           # 🔴 o monto ≥ umbral → correo a cumplimiento
POLLING_GET = 8              # GET /validaciones/{id} que hace el front mientras espera (cada 3 s)
WRU, RRU = 6, 3              # iniciar + espera + guardar (~2 KB c/u) · consulta duplicados + lecturas
BANCO_WRU, BANCO_RRU = 1, CONSULTAS_BANCO   # depósito registrado (simulación) · consultas por GSI
TOKENS = {"extraer": (2400, 250), "riesgo": (900, 600)}   # (entrada, salida) por llamada

ESCENARIOS = {"Demo académica": 1_000, "Piloto (≈2 mil clientes)": 15_000, "Crecimiento": 150_000}


def costo(n):
    trans = n * (TRANSICIONES + 2 * FRAC_REVISION)
    inv = sum(k for k, _, _ in LAMBDAS.values()) * n + n          # + StartExecution desde Operaciones (misma Lambda)
    gbs = sum(k * (mb / 1024) * (ms / 1000) for k, mb, ms in LAMBDAS.values()) * n
    correos = n * (FRAC_REVISION + FRAC_ALERTA)
    groq_ext = n * (TOKENS["extraer"][0] * P["groq_qwen_in"] + TOKENS["extraer"][1] * P["groq_qwen_out"])
    groq_rie = n * (TOKENS["riesgo"][0] * P["groq_oss_in"] + TOKENS["riesgo"][1] * P["groq_oss_out"])
    aws = {
        "AWS Step Functions (Standard)": max(0, trans - P["sfn_gratis"]) * P["sfn_transicion"],
        "AWS Lambda (4 pasos + Validaciones + banco)": inv * P["lambda_req"] + gbs * P["lambda_gbs"],
        "API Gateway (/validaciones + /banco)": n * (POLLING_GET + 2 + CONSULTAS_BANCO + 1) * P["apigw_http"],
        "DynamoDB (validaciones + banco simulado)": n * ((WRU + BANCO_WRU) * P["ddb_wru"] + (RRU + BANCO_RRU) * P["ddb_rru"]),
        "SNS (correos NexoGuard)": max(0, correos - P["sns_email_gratis"]) * P["sns_email"],
        "CloudWatch (logs + 1 alarma)": n * 6 * 1.0 / 1024 / 1024 * P["cw_ingest_gb"] + P["cw_alarm"],
    }
    groq = {"Groq qwen3.8-27b (Agente Extractor)": groq_ext, "Groq gpt-oss-20b (Agente de Riesgo)": groq_rie}
    return aws, groq, {"transiciones": trans, "lambda_invocaciones": inv, "lambda_gbs": gbs, "correos": correos}


if __name__ == "__main__":
    base = json.loads(Path("docs/costos.json").read_text(encoding="utf-8"))["escenarios"]
    res = {}
    for nombre, n in ESCENARIOS.items():
        aws, groq, m = costo(n)
        t_aws, t_groq = sum(aws.values()), sum(groq.values())
        base_total = base.get(nombre, {}).get("total")
        res[nombre] = {"validaciones": n, "aws": {k: round(v, 2) for k, v in aws.items()}, "total_aws": round(t_aws, 2),
                       "groq": {k: round(v, 2) for k, v in groq.items()}, "total_groq": round(t_groq, 2),
                       "por_validacion": round((t_aws + t_groq) / n, 4), "base_nexocambio": base_total,
                       "metricas": {k: round(v, 1) for k, v in m.items()}}
        print(f"{nombre:28s} {n:>8,d} validaciones/mes → AWS US$ {t_aws:6.2f} + Groq US$ {t_groq:7.2f}"
              f"  (US$ {(t_aws + t_groq) / n:.4f} por validación; base NexoCambio US$ {base_total})")
        for k, v in {**aws, **groq}.items():
            print(f"    {k:44s} {v:8.2f}")
    Path("docs/final/costos_nexoguard.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")

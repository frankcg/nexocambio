#!/usr/bin/env python3
"""Estimación de costo mensual de NexoCambio (us-east-1, sin capa gratuita = escenario conservador).
Precios de REFERENCIA (lista pública de AWS al momento de redactar): VALIDAR en https://calculator.aws antes de entregar."""
import json

P = dict(lambda_req=0.20 / 1e6, lambda_gbs=0.0000166667, apigw_http=1.00 / 1e6,
         ddb_wru=0.625 / 1e6, ddb_rru=0.125 / 1e6, ddb_gb=0.25,
         s3_gb=0.023, s3_put=0.005 / 1000, s3_get=0.0004 / 1000,
         cw_ingest_gb=0.50, cw_store_gb=0.03, cw_alarm=0.10, egress_gb=0.09, egress_free_gb=100)

# Mezcla de tráfico por cada request de la API
MIX = {  # accion: (fracción, servicio, memoria_MB, duración_ms, WRU, RRU)
    "cotizar":      (0.70, "cot", 256, 120, 1.0, 1.0),
    "login":        (0.04, "cli", 512, 350, 0.0, 2.0),
    "registro":     (0.01, "cli", 512, 450, 6.0, 0.0),    # transacción de 3 ítems = 2× WRU
    "crear_op":     (0.05, "ops", 512, 300, 1.0, 1.0),    # + 1 invocación a cotizaciones (~1 RRU, 120 ms)
    "comprobante":  (0.05, "ops", 512, 500, 2.0, 1.0),
    "listar":       (0.10, "ops", 512, 150, 0.0, 2.0),
    "detalle":      (0.05, "ops", 512, 150, 0.0, 1.0),
}
ESCENARIOS = {"Demo académica": 20_000, "Piloto (≈2 mil clientes)": 300_000, "Crecimiento": 3_000_000}
COMPROBANTE_KB = 400


def costo(reqs):
    lam_req = reqs + reqs * MIX["crear_op"][0]          # + invocaciones internas Ops→Cot
    gbs = sum(reqs * f * (mb / 1024) * (ms / 1000) for f, _, mb, ms, _, _ in MIX.values())
    gbs += reqs * MIX["crear_op"][0] * (256 / 1024) * 0.12
    wru = sum(reqs * f * w for f, _, _, _, w, _ in MIX.values())
    rru = sum(reqs * f * r for f, _, _, _, _, r in MIX.values()) + reqs * MIX["crear_op"][0]
    comprobantes = reqs * MIX["comprobante"][0]
    s3_gb = comprobantes * COMPROBANTE_KB / 1024 / 1024
    detalles = reqs * MIX["detalle"][0]
    logs_gb = reqs * 2 * 0.6 / 1024 / 1024               # ≈ 2 líneas de ~0.6 KB por request
    egreso_gb = (reqs * 1.2 + reqs * 0.05 * 130 + detalles * COMPROBANTE_KB) / 1024 / 1024
    d = {
        "API Gateway (HTTP API)": reqs * P["apigw_http"],
        "AWS Lambda (3 microservicios)": lam_req * P["lambda_req"] + gbs * P["lambda_gbs"],
        "DynamoDB (bajo demanda)": wru * P["ddb_wru"] + rru * P["ddb_rru"] + 0.05 * P["ddb_gb"],
        "S3 (comprobantes + sitio web)": s3_gb * P["s3_gb"] + comprobantes * P["s3_put"] + detalles * P["s3_get"] + 0.13 / 1024 * P["s3_gb"],
        "CloudWatch (logs + 4 alarmas)": logs_gb * (P["cw_ingest_gb"] + P["cw_store_gb"]) + 4 * P["cw_alarm"],
        "Transferencia de datos": max(0.0, egreso_gb - P["egress_free_gb"]) * P["egress_gb"],
        "SNS (alertas por correo)": 0.0,
    }
    return d, {"lambda_req": lam_req, "gbs": gbs, "wru": wru, "rru": rru, "s3_gb": s3_gb, "logs_gb": logs_gb, "egreso_gb": egreso_gb}


# Alternativa con contenedores (orden de magnitud, funcionando 24×7)
fargate_tarea_h = 0.25 * 0.04048 + 0.5 * 0.004445
ALT = {"ECS Fargate: 3 servicios × 2 tareas (0.25 vCPU / 0.5 GB)": 6 * fargate_tarea_h * 730,
       "Application Load Balancer": 0.0225 * 730 + 0.008 * 730,
       "RDS PostgreSQL db.t3.micro + 20 GB": 0.017 * 730 + 20 * 0.115}

if __name__ == "__main__":
    res = {}
    for n, r in ESCENARIOS.items():
        d, m = costo(r)
        res[n] = {"requests": r, "detalle": {k: round(v, 2) for k, v in d.items()}, "total": round(sum(d.values()), 2), "metricas": {k: round(v, 3) for k, v in m.items()}}
        print(f"{n:28s} {r:>9,d} req/mes  →  US$ {sum(d.values()):7.2f}")
        for k, v in d.items():
            print(f"    {k:34s} {v:8.2f}")
    alt = {k: round(v, 2) for k, v in ALT.items()}
    print("Alternativa contenedores:", alt, "total", round(sum(ALT.values()), 2))
    json.dump({"escenarios": res, "alternativa": alt, "alternativa_total": round(sum(ALT.values()), 2)}, open("docs/costos.json", "w"), indent=1, ensure_ascii=False)

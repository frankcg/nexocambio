#!/usr/bin/env bash
# Elimina TODO lo creado por deploy.sh (útil al terminar para no consumir presupuesto del Lab).
set -euo pipefail
cd "$(dirname "$0")/.."
STAGE="${STAGE:-dev}"; REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
STACK="nexocambio-${STAGE}"; ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
for b in "nexo-${STAGE}-comprobantes-${ACCOUNT}-${REGION}" "nexo-${STAGE}-web-${ACCOUNT}-${REGION}"; do
  aws s3 rm "s3://${b}" --recursive --region "$REGION" 2>/dev/null || true   # el bucket debe estar vacío
done
aws cloudformation delete-stack --stack-name "$STACK" --region "$REGION"
aws cloudformation wait stack-delete-complete --stack-name "$STACK" --region "$REGION"
aws s3 rb "s3://nexo-${STAGE}-artifacts-${ACCOUNT}-${REGION}" --force --region "$REGION" 2>/dev/null || true
echo "Stack ${STACK} eliminado."

#!/usr/bin/env bash
# Despliega NexoCambio en AWS Academy (Learner Lab) desde AWS CloudShell o una terminal con credenciales del Lab.
#   STAGE=dev AWS_REGION=us-east-1 ALERT_EMAIL=tu@correo.com ./scripts/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."

STAGE="${STAGE:-dev}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
STACK="nexocambio-${STAGE}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
ARTIFACTS="nexo-${STAGE}-artifacts-${ACCOUNT}-${REGION}"

mkdir -p .secrets
[ -f .secrets/jwt_secret ] || openssl rand -hex 32 > .secrets/jwt_secret   # estable entre despliegues
[ -f .secrets/admin_key ]  || openssl rand -hex 12 > .secrets/admin_key
JWT_SECRET="$(cat .secrets/jwt_secret)"; ADMIN_KEY="$(cat .secrets/admin_key)"

echo "==> Bucket de artefactos: s3://${ARTIFACTS}"
aws s3api head-bucket --bucket "$ARTIFACTS" --region "$REGION" 2>/dev/null || aws s3 mb "s3://${ARTIFACTS}" --region "$REGION"

echo "==> Empaquetando funciones y capa"
aws cloudformation package --template-file template.yaml --s3-bucket "$ARTIFACTS" \
    --output-template-file .packaged.yaml --region "$REGION" >/dev/null

echo "==> Desplegando stack ${STACK} (${REGION})"
aws cloudformation deploy --template-file .packaged.yaml --stack-name "$STACK" --region "$REGION" \
    --no-fail-on-empty-changeset \
    --parameter-overrides "Stage=${STAGE}" "JwtSecret=${JWT_SECRET}" "AdminKey=${ADMIN_KEY}" \
                          "AlertEmail=${ALERT_EMAIL:-}" "UsarTasasEnVivo=${USAR_TASAS_EN_VIVO:-true}"

out() { aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
API_URL="$(out ApiUrl)"; WEB_BUCKET="$(out BucketWeb)"; WEB_URL="$(out SitioWebUrl)"

echo "==> Compilando frontend Angular"
( cd frontend && npm ci && npx ng build )
python3 scripts/configurar_front.py frontend/dist/frontend/browser/config.json "$API_URL"

echo "==> Publicando frontend en s3://${WEB_BUCKET}"
aws s3 sync frontend/dist/frontend/browser/ "s3://${WEB_BUCKET}/" --delete --region "$REGION"

cat <<MSG

================ NexoCambio desplegado ================
API (usar en Postman):   ${API_URL}
Sitio web (frontend):    ${WEB_URL}
Clave back-office:       ${ADMIN_KEY}   (cabecera x-admin-key)
Prueba rápida:           curl -s -X POST ${API_URL}/cotizar -H 'content-type: application/json' \\
                           -d '{"modalidad":"casa","moneda_origen":"PEN","moneda_destino":"USD","monto_origen":1000}'
=======================================================
MSG

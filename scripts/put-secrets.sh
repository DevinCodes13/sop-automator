#!/usr/bin/env bash
# Stores production settings in AWS SSM Parameter Store (encrypted).
# Re-running is safe: existing generated passwords are kept.
set -euo pipefail
REGION=us-east-1
PREFIX=/sop-automator

put() {
  aws ssm put-parameter --region "$REGION" --name "$PREFIX/$1" --type SecureString \
    --value "$2" --overwrite > /dev/null
  echo "saved   $1"
}

put_once() {
  if aws ssm get-parameter --region "$REGION" --name "$PREFIX/$1" > /dev/null 2>&1; then
    echo "kept    $1"
  else
    put "$1" "$2"
  fi
}

put_once POSTGRES_PASSWORD "$(openssl rand -hex 24)"
put_once JWT_SECRET "$(openssl rand -hex 32)"
put_once GRAFANA_ADMIN_PASSWORD "$(openssl rand -hex 16)"

if ! aws ssm get-parameter --region "$REGION" --name "$PREFIX/ADMIN_PASSWORD" > /dev/null 2>&1; then
  read -r -s -p "Choose the production admin password (12+ characters): " ADMIN_PW; echo
  if [ "${#ADMIN_PW}" -lt 12 ]; then echo "Too short. Run again."; exit 1; fi
  put ADMIN_PASSWORD "$ADMIN_PW"
  unset ADMIN_PW
else
  echo "kept    ADMIN_PASSWORD"
fi

ANTHROPIC_KEY=$(grep '^ANTHROPIC_API_KEY=' .env | cut -d= -f2- | sed "s/^'//; s/'$//")
put ANTHROPIC_API_KEY "$ANTHROPIC_KEY"
unset ANTHROPIC_KEY

put POSTGRES_USER sop
put POSTGRES_DB sop_automator
put ADMIN_EMAIL admin@example.com
put CLAUDE_MODEL claude-haiku-5-5
put LLM_INPUT_USD_PER_MTOK 0.10
put LLM_OUTPUT_USD_PER_MTOK 0.50
put DEMO_MODE false
put SITE_ADDRESS sop.aws.vulntrack.app
echo "Done. Names stored:"
aws ssm get-parameters-by-path --region "$REGION" --path "$PREFIX" --query "Parameters[].Name" --output text | tr '\t' '\n'

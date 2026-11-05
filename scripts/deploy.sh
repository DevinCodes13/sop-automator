#!/usr/bin/env bash
# Runs ON the server (sent by GitHub through SSM). Usage: deploy.sh <git-sha>
set -euo pipefail
TAG="${1:?usage: deploy.sh <git-sha>}"
APP_DIR=/opt/sop-automator
REGION=us-east-1
PREFIX=/sop-automator
OWNER=devincodes13
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env"
cd "$APP_DIR"

echo "==> Writing settings from SSM Parameter Store"
umask 077
aws ssm get-parameters-by-path --region "$REGION" --path "$PREFIX" --with-decryption \
  --query "Parameters[].[Name,Value]" --output text |
while IFS=$'\t' read -r name value; do
  case "$value" in *"'"*) echo "ERROR: ${name##*/} contains a single quote" >&2; exit 1 ;; esac
  printf "%s='%s'\n" "${name##*/}" "$value"
done > .env.new
{
  echo "API_IMAGE=ghcr.io/$OWNER/sop-automator-api:$TAG"
  echo "WEB_IMAGE=ghcr.io/$OWNER/sop-automator-web:$TAG"
} >> .env.new
mv .env.new .env
echo "settings: $(grep -c = .env) values"

echo "==> Pulling images for ${TAG:0:7}"
$COMPOSE pull --quiet api web

echo "==> Starting"
$COMPOSE up -d --no-build --remove-orphans

echo "==> Waiting for the API and database"
for i in $(seq 1 40); do
  if $COMPOSE exec -T api python -c "import urllib.request,sys; sys.exit(0 if b'\"db\":\"ok\"' in urllib.request.urlopen('http://localhost:8000/api/health', timeout=3).read() else 1)" 2>/dev/null; then
    echo "Healthy after $i checks"
    docker image prune -f > /dev/null
    exit 0
  fi
  sleep 3
done
echo "API did not become healthy" >&2
$COMPOSE logs --tail 50 api >&2
exit 1

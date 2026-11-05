#!/usr/bin/env bash
# Deploys Saathi to Azure Container Apps: the FastAPI backend and the Blazor UI.
# Images are built in Azure (az acr build), so Docker is not needed locally; a Codespace works.
#
# Before running:
#   az login && az account set --subscription <id>
#   export the AZURE_OPENAI_* and AZURE_SEARCH_* variables you use locally (see .env.example)
# Usage: scripts/deploy_azure.sh            (safe to re-run; it updates what exists)
set -euo pipefail

RG=${RG:-saathi-rg}
LOCATION=${LOCATION:-centralus}
SUFFIX=${SUFFIX:-$(az account show --query id -o tsv | tr -d '-' | cut -c1-6)}
ACR=${ACR:-saathiacr$SUFFIX}
ENV_NAME=${ENV_NAME:-saathi-env}
API_APP=${API_APP:-saathi-api}
WEB_APP=${WEB_APP:-saathi-web}
TAG=${TAG:-$(git rev-parse --short HEAD)}

need() { for v in "$@"; do [ -n "${!v:-}" ] || { echo "Set $v first (see .env.example)"; exit 1; }; done; }
need AZURE_OPENAI_ENDPOINT AZURE_OPENAI_API_KEY AZURE_OPENAI_DEPLOYMENT AZURE_OPENAI_EMBED_DEPLOYMENT \
     AZURE_SEARCH_ENDPOINT AZURE_SEARCH_INDEX_NAME AZURE_SEARCH_ADMIN_KEY

az extension add --name containerapp --upgrade --only-show-errors
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait
az provider register --namespace Microsoft.ContainerRegistry --wait

echo "== Resource group, registry and Container Apps environment"
az group create -n "$RG" -l "$LOCATION" -o none
az acr show -n "$ACR" -g "$RG" -o none 2>/dev/null || az acr create -n "$ACR" -g "$RG" --sku Basic --admin-enabled true -o none
az containerapp env show -n "$ENV_NAME" -g "$RG" -o none 2>/dev/null || az containerapp env create -n "$ENV_NAME" -g "$RG" -l "$LOCATION" -o none

echo "== Building images in Azure (API takes ~10 minutes the first time)"
az acr build -r "$ACR" -t "saathi-api:$TAG" . -o none
az acr build -r "$ACR" -t "saathi-web:$TAG" dotnet -o none

REGISTRY="$ACR.azurecr.io"
ACR_USER=$(az acr credential show -n "$ACR" --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR" --query 'passwords[0].value' -o tsv)

echo "== API container app"
# Keys go in as Container Apps secrets, never as plain environment values.
SECRETS="openai-key=$AZURE_OPENAI_API_KEY search-key=$AZURE_SEARCH_ADMIN_KEY"
API_ENV="LLM_PROVIDER=azure RETRIEVER=azure INTENT_PROVIDER=tfidf_lr ML_PROVIDER=local QUERY_REWRITE=${QUERY_REWRITE:-llm} \
SAATHI_AS_OF_DATE=${SAATHI_AS_OF_DATE:-2026-10-28} \
AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT AZURE_OPENAI_DEPLOYMENT=$AZURE_OPENAI_DEPLOYMENT \
AZURE_OPENAI_EMBED_DEPLOYMENT=$AZURE_OPENAI_EMBED_DEPLOYMENT AZURE_OPENAI_API_KEY=secretref:openai-key \
AZURE_SEARCH_ENDPOINT=$AZURE_SEARCH_ENDPOINT AZURE_SEARCH_INDEX_NAME=$AZURE_SEARCH_INDEX_NAME \
AZURE_SEARCH_ADMIN_KEY=secretref:search-key"
if az containerapp show -n "$API_APP" -g "$RG" -o none 2>/dev/null; then
  az containerapp secret set -n "$API_APP" -g "$RG" --secrets $SECRETS -o none
  az containerapp update -n "$API_APP" -g "$RG" --image "$REGISTRY/saathi-api:$TAG" --set-env-vars $API_ENV -o none
else
  # One replica: session memory and the audit chain live in the process.
  az containerapp create -n "$API_APP" -g "$RG" --environment "$ENV_NAME" \
    --image "$REGISTRY/saathi-api:$TAG" --registry-server "$REGISTRY" \
    --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --ingress external --target-port 8000 --cpu 1 --memory 2Gi --min-replicas 1 --max-replicas 1 \
    --secrets $SECRETS --env-vars $API_ENV -o none
fi
API_URL="https://$(az containerapp show -n "$API_APP" -g "$RG" --query properties.configuration.ingress.fqdn -o tsv)"

echo "== Web container app"
if az containerapp show -n "$WEB_APP" -g "$RG" -o none 2>/dev/null; then
  az containerapp update -n "$WEB_APP" -g "$RG" --image "$REGISTRY/saathi-web:$TAG" --set-env-vars "Saathi__ApiUrl=$API_URL" -o none
else
  az containerapp create -n "$WEB_APP" -g "$RG" --environment "$ENV_NAME" \
    --image "$REGISTRY/saathi-web:$TAG" --registry-server "$REGISTRY" \
    --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --ingress external --target-port 8080 --cpu 0.5 --memory 1Gi --min-replicas 1 --max-replicas 1 \
    --env-vars "Saathi__ApiUrl=$API_URL" -o none
fi
WEB_URL="https://$(az containerapp show -n "$WEB_APP" -g "$RG" --query properties.configuration.ingress.fqdn -o tsv)"

echo "== Smoke check"
for i in $(seq 1 30); do curl -fsS "$API_URL/health" && break; sleep 10; done
echo
echo "API: $API_URL/docs"
echo "UI:  $WEB_URL"
echo "Delete everything after the demo: az group delete -n $RG --yes --no-wait"

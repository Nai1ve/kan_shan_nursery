#!/usr/bin/env bash
# Kanshan deployment script
#
# Usage:
#   bash scripts/deploy.sh           # Start containers
#   bash scripts/deploy.sh --build   # Rebuild images and start
#   bash scripts/deploy.sh --down    # Stop containers
#   bash scripts/deploy.sh --logs    # View logs
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="${ROOT}/infra"

# Ensure .env exists
if [[ ! -f "${INFRA_DIR}/.env" ]]; then
  echo "[deploy] No .env found. Copying from .env.deploy..."
  cp "${INFRA_DIR}/.env.deploy" "${INFRA_DIR}/.env"
fi

cd "${INFRA_DIR}"

case "${1:-}" in
  --build)
    echo "[deploy] Building images and starting containers..."
    docker compose build
    docker compose up -d
    echo "[deploy] Containers started. Use 'bash scripts/deploy.sh --logs' to view logs."
    ;;
  --down)
    echo "[deploy] Stopping containers..."
    docker compose down
    ;;
  --logs)
    docker compose logs -f
    ;;
  "")
    echo "[deploy] Starting containers..."
    docker compose up -d
    echo "[deploy] Containers started. Use 'bash scripts/deploy.sh --logs' to view logs."
    ;;
  *)
    echo "Usage: bash scripts/deploy.sh [--build|--down|--logs]"
    exit 1
    ;;
esac

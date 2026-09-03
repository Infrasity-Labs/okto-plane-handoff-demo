#!/usr/bin/env bash
# Bootstrap: Plane stack + Pulse + Nexus, one command.
#
# Prereqs (not installed by this script):
#   - Docker (with Compose v2) — required for the Plane stack (API, web,
#     live, Postgres, Redis, MinIO, RabbitMQ). Nothing here works without it.
#   - okto-pulse and okto-nexus CLIs installed (see each product's own docs).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLANE_DIR="$ROOT_DIR/plane"
mkdir -p "$ROOT_DIR/demo-state"

echo "==> 1/4 Scaffolding Plane's env files"
cd "$PLANE_DIR"
if [ ! -f .env ]; then
  bash setup.sh || true  # Plane's own env-file scaffolder; the pnpm/corepack
                          # step it also runs is optional for the compose path
fi

echo "==> 2/4 Fixing two known local-dev env gaps (see docs/architecture.md)"
# Plane's shipped local-dev .env.example points the async export pipeline at
# a container-unreachable MinIO endpoint and disables MinIO outright — the
# export job can never complete locally with the shipped defaults.
if grep -q '^USE_MINIO=0' apps/api/.env 2>/dev/null; then
  sed -i.bak 's/^USE_MINIO=0/USE_MINIO=1/' apps/api/.env
  sed -i.bak 's#^AWS_S3_ENDPOINT_URL="http://localhost:9000"#AWS_S3_ENDPOINT_URL="http://plane-minio:9000"#' apps/api/.env
  rm -f apps/api/.env.bak
  echo "    Fixed apps/api/.env: USE_MINIO=1, AWS_S3_ENDPOINT_URL -> plane-minio:9000"
fi

echo "==> 3/4 Bringing up the Plane stack (docker compose)"
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed/on PATH. Install Docker Desktop (or Colima) first." >&2
  exit 1
fi
docker compose up -d
echo "    Waiting for the stack to report healthy..."
# TODO: poll `docker compose ps` / a health endpoint once the stack is up
# rather than a fixed sleep.

echo "==> 4/4 Starting Pulse + Nexus"
cd "$ROOT_DIR"
# okto-pulse serve reads its working directory as the project root for
# board/spec scoping — point it at okto-plane-handoff-demo/, not plane/,
# so the demo's own board state stays separate from the forked repo.
nohup okto-pulse serve > "$ROOT_DIR/demo-state/pulse-serve.log" 2>&1 &
echo "    Pulse: http://127.0.0.1:8100  (MCP :8101)"

nohup okto-nexus serve --project-root "$PLANE_DIR" > "$ROOT_DIR/demo-state/nexus-serve.log" 2>&1 &
echo "    Nexus: http://127.0.0.1:8202"

echo "==> Done. Register agents (spec-agent, backend-agent, frontend-agent,"
echo "    validator-agent) in Nexus and point each MCP client at both"
echo "    servers before starting the live run. See docs/walkthrough.md for"
echo "    the e2e bootstrap-user script and the next step for a full e2e pass."

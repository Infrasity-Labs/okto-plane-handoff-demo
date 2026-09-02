#!/usr/bin/env bash
# Bootstrap: Plane stack + Pulse + Nexus, one command.
#
# Prereqs (not installed by this script):
#   - Docker (with Compose v2) — required for the Plane stack (API, web,
#     live, Postgres, Redis, MinIO). Nothing here works without it.
#   - okto-pulse and okto-nexus CLIs installed (see each repo's own
#     CLAUDE.md for install instructions).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLANE_DIR="$ROOT_DIR/plane"

echo "==> 1/3 Bringing up the Plane stack (docker compose)"
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed/on PATH. Install Docker Desktop (or Colima) first." >&2
  exit 1
fi
cd "$PLANE_DIR"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "    Created plane/.env from .env.example — review before first run."
fi
docker compose up -d
echo "    Waiting for the stack to report healthy..."
# TODO: poll `docker compose ps` / a health endpoint once the stack is up
# rather than a fixed sleep — fill in during the live run.

echo "==> 2/3 Starting Pulse (governance layer) against this repo"
cd "$ROOT_DIR"
# okto-pulse serve reads its working directory as the project root for
# board/spec scoping — point it at okto-plane-handoff-demo/, not plane/,
# so the demo's own board state stays separate from the forked repo.
nohup okto-pulse serve > "$ROOT_DIR/.pulse/serve.log" 2>&1 &
echo "    Pulse: http://127.0.0.1:8100  (MCP :8101)"

echo "==> 3/3 Starting Nexus (coordination layer) pointed at plane/"
nohup okto-nexus serve --project-root "$PLANE_DIR" > "$ROOT_DIR/.nexus/serve.log" 2>&1 &
echo "    Nexus: http://127.0.0.1:8202"

echo "==> Done. Register agents (spec-agent, backend-agent, frontend-agent,"
echo "    validator-agent) in Nexus and point each MCP client at both"
echo "    servers before starting the live run."

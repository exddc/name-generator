#!/usr/bin/env bash
# Mandatory verification baseline (TW-233).
# CI jobs call the same targets as local developers.
#
# Usage:
#   ./scripts/verify.sh --fast              # lint, typecheck, build, unit tests
#   ./scripts/verify.sh --full              # fast + e2e + integration + audits + containers
#   ./scripts/verify.sh web                 # web lint/typecheck/build
#   ./scripts/verify.sh web-e2e             # browser contract (Playwright)
#   ./scripts/verify.sh api                 # API unit tests (no integration)
#   ./scripts/verify.sh api-integration     # Postgres/Redis integration (services required)
#   ./scripts/verify.sh worker              # worker unit tests
#   ./scripts/verify.sh supply-chain        # dep audits + compose/Dockerfile + optional Trivy
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BUN_VERSION="${BUN_VERSION:-1.3.0}"
POETRY_VERSION="${POETRY_VERSION:-1.8.5}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12.13}"

log() { printf '\n==> %s\n' "$*"; }

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: required command not found: $1" >&2
    exit 1
  fi
}

install_web_deps() {
  need_cmd bun
  log "Install web dependencies (bun ${BUN_VERSION}+)"
  (cd apps/web && bun install --frozen-lockfile)
}

install_api_deps() {
  need_cmd poetry
  log "Install API dependencies"
  (cd apps/api && poetry install --no-interaction --no-ansi)
}

install_worker_deps() {
  need_cmd poetry
  log "Install worker dependencies"
  (cd apps/worker && poetry install --no-interaction --no-ansi)
}

verify_web() {
  install_web_deps
  log "Web lint"
  (cd apps/web && bun run lint)
  log "Web typecheck"
  (cd apps/web && bun run typecheck)
  log "Web build"
  (
    cd apps/web
    API_JWT_SECRET="${API_JWT_SECRET:-ci-only-api-jwt-secret-at-least-32-bytes}" \
    BETTER_AUTH_SECRET="${BETTER_AUTH_SECRET:-ci-only-better-auth-secret-at-least-32-bytes}" \
    NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://127.0.0.1:8000}" \
    NEXT_PUBLIC_BETTER_AUTH_URL="${NEXT_PUBLIC_BETTER_AUTH_URL:-http://127.0.0.1:3100}" \
    BETTER_AUTH_URL="${BETTER_AUTH_URL:-http://127.0.0.1:3100}" \
    bun run build
  )
}

verify_web_e2e() {
  install_web_deps
  need_cmd bun
  log "Playwright browser install (chromium)"
  (cd apps/web && bunx playwright install chromium)
  log "Browser contract (mocked UI; API owns server contracts)"
  (
    cd apps/web
    export CI="${CI:-}"
    API_JWT_SECRET="${API_JWT_SECRET:-ci-only-api-jwt-secret-at-least-32-bytes}" \
    BETTER_AUTH_SECRET="${BETTER_AUTH_SECRET:-ci-only-better-auth-secret-at-least-32-bytes}" \
    NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://127.0.0.1:8000}" \
    NEXT_PUBLIC_BETTER_AUTH_URL="${NEXT_PUBLIC_BETTER_AUTH_URL:-http://127.0.0.1:3100}" \
    BETTER_AUTH_URL="${BETTER_AUTH_URL:-http://127.0.0.1:3100}" \
    bun run test:e2e:ci
  )
}

verify_api_unit() {
  install_api_deps
  log "API unit tests"
  (
    cd apps/api
    API_JWT_SECRET="${API_JWT_SECRET:-ci-only-api-jwt-secret-at-least-32-bytes}" \
    GROQ_VALIDATE_MODEL_ON_STARTUP="${GROQ_VALIDATE_MODEL_ON_STARTUP:-false}" \
    poetry run pytest -q -m "not integration"
  )
}

verify_api_integration() {
  install_api_deps
  log "API integration tests (Postgres + Redis required)"
  (
    cd apps/api
    export RUN_POSTGRES_INTEGRATION_TEST="${RUN_POSTGRES_INTEGRATION_TEST:-1}"
    export RUN_REDIS_INTEGRATION_TEST="${RUN_REDIS_INTEGRATION_TEST:-1}"
    export TEST_DATABASE_ADMIN_URL="${TEST_DATABASE_ADMIN_URL:-postgresql://postgres:password@127.0.0.1:5432/postgres}"
    export TEST_REDIS_URL="${TEST_REDIS_URL:-redis://127.0.0.1:6379/15}"
    export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/15}"
    export API_JWT_SECRET="${API_JWT_SECRET:-ci-only-api-jwt-secret-at-least-32-bytes}"
    export GROQ_VALIDATE_MODEL_ON_STARTUP="${GROQ_VALIDATE_MODEL_ON_STARTUP:-false}"
    poetry run pytest -q -m integration
  )
}

verify_worker() {
  install_worker_deps
  log "Worker tests"
  (cd apps/worker && poetry run pytest -q)
}

audit_web() {
  install_web_deps
  log "Web dependency audit (high+)"
  (cd apps/web && bun audit --audit-level=high)
}

audit_api() {
  install_api_deps
  need_cmd pipx
  log "API production dependency audit"
  (
    cd apps/api
    poetry export --without-hashes --without dev | pipx run pip-audit==2.10.1 -r /dev/stdin
  )
}

audit_worker() {
  install_worker_deps
  need_cmd pipx
  log "Worker production dependency audit"
  (
    cd apps/worker
    poetry export --without-hashes --without dev | pipx run pip-audit==2.10.1 -r /dev/stdin
  )
}

verify_containers() {
  need_cmd docker
  log "Compose config validation"
  GROQ_API_KEY="${GROQ_API_KEY:-ci-placeholder}" \
    docker compose --profile infra --profile backend --profile frontend config --quiet
  log "Dockerfile checks (no full image build)"
  docker build --check apps/api
  docker build --check apps/worker
  docker build --check apps/web
}

verify_trivy() {
  if ! command -v trivy >/dev/null 2>&1; then
    echo "note: trivy not installed locally; CI runs the secret/misconfig scan" >&2
    return 0
  fi
  log "Trivy secret + misconfig scan"
  trivy fs \
    --scanners misconfig,secret \
    --severity CRITICAL,HIGH \
    --ignore-unfixed \
    --exit-code 1 \
    --skip-dirs apps/web/node_modules,apps/api/.venv,apps/worker/.venv \
    .
}

verify_supply_chain() {
  audit_web
  audit_api
  audit_worker
  verify_containers
  verify_trivy
}

usage() {
  sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
}

MODE="${1:-}"
if [[ -z "$MODE" ]]; then
  usage
  exit 2
fi

case "$MODE" in
  -h|--help|help)
    usage
    ;;
  --fast)
    verify_web
    verify_api_unit
    verify_worker
    log "Fast verification passed"
    ;;
  --full)
    verify_web
    verify_web_e2e
    verify_api_unit
    verify_api_integration
    verify_worker
    verify_supply_chain
    log "Full verification passed"
    ;;
  web)
    verify_web
    ;;
  web-e2e)
    verify_web_e2e
    ;;
  api)
    verify_api_unit
    ;;
  api-integration)
    verify_api_integration
    ;;
  worker)
    verify_worker
    ;;
  supply-chain)
    verify_supply_chain
    ;;
  *)
    echo "error: unknown target: $MODE" >&2
    usage
    exit 2
    ;;
esac

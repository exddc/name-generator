#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="${SCRIPT_DIR}/../better-auth_migrations/2025-10-30T10-28-39.139Z.sql"

if [[ ! -f "${SQL_FILE}" ]]; then
    echo "Migration file not found at ${SQL_FILE}" >&2
    exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
    echo "psql is not installed in this container. Install postgresql-client first." >&2
    exit 1
fi

PGHOST="${POSTGRES_HOST:-${DB_HOST:-127.0.0.1}}"
PGPORT="${POSTGRES_PORT:-${DB_PORT:-5432}}"
PGUSER="${POSTGRES_USER:-${DB_USER:-postgres}}"
PGPASSWORD_VALUE="${POSTGRES_PASSWORD:-${DB_PASSWORD:-password}}"
PGDATABASE="${POSTGRES_DB:-${DB_NAME:-domain_generator}}"
PGSSLMODE="${PGSSLMODE:-prefer}"

export PGPASSWORD="${PGPASSWORD_VALUE}"

echo "Seeding Better Auth tables into ${PGUSER}@${PGHOST}:${PGPORT}/${PGDATABASE} ..."

psql "host=${PGHOST} port=${PGPORT} user=${PGUSER} dbname=${PGDATABASE} sslmode=${PGSSLMODE}" -f "${SQL_FILE}"

echo "Better Auth tables seeded successfully."


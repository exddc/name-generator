# API

## Getting Started

### Requirements

- **Python 3.12 or higher**
- **Poetry**: Install Poetry with: `curl -sSL https://install.python-poetry.org | python3 -`
- **Git**

### Installation

Clone the repository:

```bash
git clone https://github.com/timo-weiss/domain-generator.git
cd domain-generator/apps/api
```

Install dependencies:

```bash
poetry install
```

Run the application:

```bash
poetry run uvicorn api.main:singleton --host 0.0.0.0 --port 8000
```

### Database Setup

#### Prerequisites

Running PostgreSQL database is required.

#### Database Migrations

This service uses **Aerich** for schema management with TortoiseORM. All migrations are tracked in the `migrations/` directory.

**First Time Setup:**

```bash
./migrate.sh init
```

**Making Changes to Models:**

1. Edit models in `src/api/models/db_models.py`
2. Generate migration:
   ```bash
   ./migrate.sh migrate "description of the change"
   # or: poetry run aerich migrate --name "description of the change"
   ```
3. Apply migration:
   ```bash
   ./migrate.sh upgrade
   # or: poetry run aerich upgrade
   ```

### API Documentation

API documentation is available at http://localhost:8000/docs.

## Authentication

All production endpoints are protected with a short-lived JWT that must be supplied via the standard `Authorization: Bearer <token>` header. The API validates the token using the following environment variables:

| Variable | Description |
| --- | --- |
| `API_JWT_SECRET` | Shared HMAC secret used to verify signatures |
| `API_JWT_ISSUER` | Expected issuer claim (defaults to `domain-generator-web`) |
| `API_JWT_AUDIENCE` | Expected audience claim (defaults to `domain-generator-api`) |
| `API_JWT_ALGORITHM` | Signing algorithm (`HS256` by default) |
| `API_JWT_TTL_SECONDS` | Default lifetime for UI-issued tokens |

### Generating tokens locally

For manual testing (Bruno, curl, etc.) you can mint a token locally without the frontend by running:

```bash
cd apps/api
poetry run python scripts/generate_jwt.py --user-id <uuid-from-better-auth> --email you@example.com
```

Add `--scopes metrics:read` when you need to call the metrics endpoints. The command prints a bearer token that you can paste into `$Authorization` headers or the `{{api_token}}` variable in the Bruno collection.
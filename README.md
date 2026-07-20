# Name Generator

Webpage for generating and checking domain names, composed of a Next.js frontend, FastAPI backend, and background workers.

## Project Structure

```plaintext
.
├── apps/
│   ├── api/        # FastAPI backend service
│   ├── web/        # Next.js frontend application
│   └── worker/     # Python background worker for domain checks
├── docker-compose.yaml
└── README.md
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 22.23.1 and npm
- Python 3.12+ & Poetry

### Environment Setup

1.  Copy `.env.example` to `.env` and fill in the required secrets.
2.  Optional: set `WORKER_REPLICAS` or override ports/URLs to taste. The other values have sensible defaults from the app configs.

### Running with Docker Compose

The full stack can be started with profiles for infra, backend, and frontend. Worker count is controlled via `WORKER_REPLICAS` using Compose compatibility via `deploy.replicas`:

```bash
# Start everything
WORKER_REPLICAS=2 docker compose --compatibility \
  --profile infra --profile backend --profile frontend \
  up --build -d
```

### Development

For development instructions, refer to the specific application documentation in the `apps/` directory:

-   **Frontend**: [apps/web/README.md](apps/web/README.md)
-   **API**: [apps/api/README.md](apps/api/README.md)
-   **Worker**: [apps/worker/README.md](apps/worker/README.md)

The api endpoints can be tested with the [Bruno](https://github.com/usebruno/bruno) client. The collections are in the `apps/api/collections/` directory.

## Required verification baseline

The commands below are the same gates run for every pull request. They are
designed to work from a clean checkout with Node.js 22.23.1, Python 3.12.13, Poetry
1.8.5, and Docker available.

Install dependencies once:

```bash
cd apps/web && npm ci
cd ../api && poetry install --no-interaction --no-ansi
cd ../worker && poetry install --no-interaction --no-ansi
cd ../..
```

Run the required fast checks:

```bash
cd apps/web && npm run lint
npm run typecheck
npm run build
cd ../api && poetry run pytest -q
cd ../worker && poetry run pytest -q
```

Run the Postgres and Redis integration checks:

```bash
docker run --rm -d --name name-generator-test-postgres \
  -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:18.4-alpine
docker run --rm -d --name name-generator-test-redis \
  -p 6379:6379 redis:7.4.9-alpine

cd apps/api
RUN_POSTGRES_INTEGRATION_TEST=1 RUN_REDIS_INTEGRATION_TEST=1 \
TEST_DATABASE_ADMIN_URL=postgresql://postgres:password@127.0.0.1:5432/postgres \
TEST_REDIS_URL=redis://127.0.0.1:6379/15 \
REDIS_URL=redis://127.0.0.1:6379/15 \
API_JWT_SECRET=test-only-secret-at-least-32-bytes \
GROQ_VALIDATE_MODEL_ON_STARTUP=false \
poetry run pytest -q -m integration

cd ../..
docker stop name-generator-test-postgres name-generator-test-redis
```

Run the deterministic mocked browser contract. It verifies anonymous generation
and authenticated save/rate UI behavior, but deliberately stubs auth, API, and
provider boundaries; the API integration suite owns those server contracts.

```bash
cd apps/web
npx playwright install chromium
npm run test:e2e:ci
```

CI uses one bounded runner to avoid duplicated checkouts and dependency installs.
That runner executes all application and integration tests, audits production
dependencies, scans the working tree for secrets and high/critical findings,
and validates Compose plus every Dockerfile without paying to build three full
images on each pull request. Configure the repository ruleset to require the
single `CI required` check before merging.

### Authentication for Bruno

To interact with the protected API endpoints via Bruno:

1.  **Generate a Token**:
    Run the helper script in the `apps/api` directory:

    ```bash
    # Ensure you have the API_JWT_SECRET environment variable set (see apps/api/.env or export it in the terminal)
    export API_JWT_SECRET=your_secret_here
    cd apps/api
    poetry run python scripts/generate_jwt.py --user-id "local-test-user" --email "test@example.com" --scopes metrics:read
    ```

2.  **Set the token in Bruno**:
    *   Open the collection in Bruno.
    *   Navigate to **Collection Settings > Authentication**.
    *   Select **Bearer Token** authentication method.
    *   Paste the token into the **Token** field.


## Services

-   **API**: FastAPI application at `http://localhost:8000`
-   **Web App**: Next.js application at `http://localhost:3000`
-   **Worker**: Python background worker
-   **Postgres**: Database service
-   **Redis**: Queue and caching service

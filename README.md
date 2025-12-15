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
- Bun
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
-   **Web App**: Bun application at `http://localhost:3000`
-   **Worker**: Python background worker
-   **Postgres**: Database service
-   **Redis**: Queue and caching service

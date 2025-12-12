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

1.  Review the `docker-compose.yaml` and individual app READMEs for required environment variables.
2.  Create a `.env` file in the root directory if needed to override defaults for Docker services.

### Running with Docker Compose

The core infrastructure can be started using Docker Compose:

```bash
# Start all backend services
docker-compose --profile dev --profile api --profile worker up -d
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

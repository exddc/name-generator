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
# Backend

## Development

To run the service in development mode, use the following command:

```bash
docker build --tag backend .
docker run -p 8000:8000 backend
```

```bash
poetry run python -m src.backend.main
```
# Domain Checker Service

This service checks the availability of domain names.

## Installation

1. Install dependencies with Poetry:
    ```bash
    poetry install
    ```
2. Run the service:
   `bash
poetry run python src/domain_checker/main.py
    `

## Tests

Run the tests with Poetry:

```bash
poetry run pytest
```

## Development

To run the service in development mode, use the following command:

```bash
docker build --tag domain_checker .
docker run -p 8001:8001 domain_checker
```

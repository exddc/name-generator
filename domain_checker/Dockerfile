# Dockerfile for domain_checker service
FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install

COPY src/ ./src

CMD ["poetry", "run", "python", "src/domain_checker/main.py"]
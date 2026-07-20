FROM python:3.12.13-slim

WORKDIR /app

ARG API_PORT=8000
ENV API_PORT=${API_PORT}
ARG CORS_ALLOW_ORIGINS="http://localhost:3000"
ENV CORS_ALLOW_ORIGINS=${CORS_ALLOW_ORIGINS}
ENV PYTHONPATH=/app/src
ENV POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update && apt-get install -y --no-install-recommends whois && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* README.md /app/
COPY src /app/src

RUN pip install --no-cache-dir poetry==1.8.5

RUN poetry install --no-interaction --no-ansi --without dev

COPY . /app

RUN groupadd --system --gid 1001 app \
    && useradd --system --create-home --uid 1001 --gid app app
USER app

EXPOSE ${API_PORT}

CMD ["python", "-m", "api.main"]

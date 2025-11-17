FROM python:3.11-slim

WORKDIR /app

ARG DOMAIN_CHECKER_PORT=8080
ENV DOMAIN_CHECKER_PORT=${DOMAIN_CHECKER_PORT}
ENV PYTHONUNBUFFERED=1 \
    DOMAIN_CHECKER_DNS_TIMEOUT=3.0 \
    PYTHONPATH=/app/src \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update && apt-get install -y --no-install-recommends whois \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* README.md /app/
COPY src /app/src

RUN pip install --no-cache-dir poetry==1.8.5

RUN poetry install --no-interaction --no-ansi --without dev

COPY . /app

EXPOSE ${DOMAIN_CHECKER_PORT}

CMD ["python", "-m", "domain_checker.main"]
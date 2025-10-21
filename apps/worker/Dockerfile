FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    DOMAIN_CHECKER_PORT=8080 \
    DOMAIN_CHECKER_DNS_TIMEOUT=3.0

RUN apt-get update && apt-get install -y --no-install-recommends whois \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* README.md /app/

RUN pip install --no-cache-dir poetry==1.8.5

RUN poetry install --no-interaction --no-ansi --without dev

COPY . /app

EXPOSE ${DOMAIN_CHECKER_PORT:-8080}

CMD ["poetry", "run", "python", "src/domain_checker/main.py"]
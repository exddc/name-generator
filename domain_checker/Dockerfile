FROM python:3.11-slim

ARG DOMAIN_CHECKER_PORT
ARG DOMAIN_CHECKER_DNS_TIMEOUT

ENV PORT=${DOMAIN_CHECKER_PORT}
ENV DNS_TIMEOUT=${DOMAIN_CHECKER_DNS_TIMEOUT}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends whois \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* README.md /app/

RUN pip install --no-cache-dir poetry==1.8.5

RUN poetry install --no-interaction --no-ansi --without dev

COPY . /app

EXPOSE ${PORT}

CMD ["poetry", "run", "python", "src/domain_checker/main.py"]
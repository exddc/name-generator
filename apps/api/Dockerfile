FROM python:3.12-slim

WORKDIR /app

ARG API_PORT=8000
ENV API_PORT=${API_PORT}
ENV PYTHONPATH=/app/src
ENV POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update && apt-get install -y --no-install-recommends whois && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* README.md /app/
COPY src /app/src

RUN pip install --no-cache-dir poetry==1.8.5

RUN poetry install --no-interaction --no-ansi --without dev

COPY . /app

EXPOSE ${API_PORT}

CMD ["python", "-m", "api.main"]
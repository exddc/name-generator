FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends whois \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* README.md /app/

RUN pip install --no-cache-dir poetry==1.8.5

RUN poetry install --no-interaction --no-ansi --without dev

COPY . /app

EXPOSE 8001

CMD ["poetry", "run", "python", "src/domain_checker/main.py"]
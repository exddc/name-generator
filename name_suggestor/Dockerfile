FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml poetry.lock* README.md .env /app/

RUN pip install --no-cache-dir poetry==1.8.5

RUN poetry install --no-interaction --no-ansi --without dev

COPY . /app

EXPOSE 8002

CMD ["poetry", "run", "python", "src/name_suggestor/main.py"]
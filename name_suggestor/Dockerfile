FROM python:3.11-slim

ARG GROQ_API_KEY
ARG NUMBER_OF_SUGGESTIONS
ARG LLM_MODEL
ARG NAME_SUGGESTOR_PORT

ENV GROQ_API_KEY=${GROQ_API_KEY}
ENV NUMBER_OF_SUGGESTIONS=${NUMBER_OF_SUGGESTIONS}
ENV LLM_MODEL=${LLM_MODEL}
ENV PORT=${NAME_SUGGESTOR_PORT}

WORKDIR /app

COPY pyproject.toml poetry.lock* README.md /app/

RUN pip install --no-cache-dir poetry==1.8.5

RUN poetry install --no-interaction --no-ansi --without dev

COPY . /app

EXPOSE ${NAME_SUGGESTOR_PORT}

CMD ["poetry", "run", "python", "src/name_suggestor/main.py"]
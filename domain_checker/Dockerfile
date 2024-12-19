FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy project files
COPY ./src ./src
COPY ./pyproject.toml ./poetry.lock* ./

# Install Poetry
RUN pip install --no-cache-dir poetry

# Install dependencies
RUN poetry install --no-root --no-dev

# Expose the FastAPI app port
EXPOSE 8000

# Run the FastAPI app
CMD ["poetry", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Local Track B API image (SQLite-backed platform; Postgres optional via compose).
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ATTICUS_CONFIG_PATH=/app/config/atticus.example.yaml \
    ATTICUS_TELEMETRY=1

COPY pyproject.toml README.md AGENTS.md SPEC.md ./
COPY atticus ./atticus
COPY config ./config
COPY prompts ./prompts
COPY evals ./evals
COPY scripts ./scripts

RUN pip install --no-cache-dir -e ".[api]"

EXPOSE 8000
CMD ["atticus-api", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml alembic.ini ./
COPY src ./src
COPY migrations ./migrations
COPY scripts ./scripts

RUN python -m pip install .

RUN mkdir -p /data/raw

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "firsat_radari.main:app", "--host", "0.0.0.0", "--port", "8000"]

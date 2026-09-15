# PanScience Video Dubbing

Foundation service with FastAPI, PostgreSQL/SQLAlchemy/Alembic job persistence,
Redis/Celery workers, JSON logging, and dependency-aware health checks.

## Run

```bash
cp .env.example .env
docker compose up --build -d
curl http://localhost:8000/health
```

The API container applies Alembic migrations before starting. Run tests locally with:

```bash
python -m pip install -e '.[test]'
pytest
```

No AI providers or media-processing pipeline is implemented yet.

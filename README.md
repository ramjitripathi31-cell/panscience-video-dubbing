# PanScience Video Dubbing

Foundation service with FastAPI, PostgreSQL/SQLAlchemy/Alembic job persistence,
Redis/Celery workers, JSON logging, and dependency-aware health checks.

## Run

```bash
cp .env.example .env
docker compose up --build -d
curl http://localhost:8000/health
```

Uploads are limited to 10 minutes by default (`MAX_DURATION_SECONDS=600`).
Retries are manual and bounded by `MAX_RETRIES`; no automatic retry framework is enabled.

The API container applies Alembic migrations before starting. Run tests locally with:

```bash
python -m pip install -e '.[test]'
pytest
```

Default STT is deterministic demo mode (`STT_PROVIDER=demo`). Optional local
SpeechToText uses faster-whisper (`STT_PROVIDER=faster_whisper`; install the
`whisper` extra). Diarization, translation, and TTS remain deterministic demo
providers in the default assignment demo; no paid/cloud AI integrations are included.

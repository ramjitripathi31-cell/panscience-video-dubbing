# Configuration Guide

Configuration is loaded through Pydantic Settings. Local development can
copy `.env.example` to `.env`. Docker Compose also exposes key settings
through environment-variable substitution.

## Quick Start

``` bash
cp .env.example .env
docker compose up --build -d
curl http://localhost:8000/health
```

## Core Settings

  ---------------------------------------------------------------------------------
  Variable                                            Default Purpose
  ------------------------------ ---------------------------- ---------------------
  `APP_ENV`                                     `development` application
                                                              environment

  `LOG_LEVEL`                                          `INFO` logging level

  `API_PORT`                                           `8000` host port used by
                                                              Docker Compose

  `MAX_UPLOAD_SIZE_MB`                                  `500` upload size limit

  `MAX_DURATION_SECONDS`                                `600` maximum video
                                                              duration; 10 minutes

  `PROCESSING_TIMEOUT_SECONDS`                         `3600` configured processing
                                                              timeout

  `MAX_RETRIES`                                           `2` retry budget used by
                                                              manual retry rules

  `WORKER_CONCURRENCY`                                    `2` configured Celery
                                                              worker concurrency

  `STORAGE_ROOT`                                  `./storage` local storage root
                                                              outside Compose
  ---------------------------------------------------------------------------------

Allowed extensions in application configuration are: - `.mp4` - `.mov` -
`.mkv` - `.webm` - `.avi`

## Database and Queue

  ------------------------------------------------------------------------------
  Variable                  Default/example              Purpose
  ------------------------- ---------------------------- -----------------------
  `POSTGRES_DB`             `panscience`                 Compose PostgreSQL
                                                         database

  `POSTGRES_USER`           `panscience`                 Compose PostgreSQL user

  `POSTGRES_PASSWORD`       `change-me` in sample env    PostgreSQL password

  `DATABASE_URL`            PostgreSQL DSN               application database
                                                         connection

  `REDIS_URL`               `redis://localhost:6379/0`   Redis connection
                            locally                      

  `CELERY_BROKER_URL`       falls back to `REDIS_URL`    optional explicit
                                                         broker

  `CELERY_RESULT_BACKEND`   falls back to `REDIS_URL`    optional result backend
  ------------------------------------------------------------------------------

Inside Docker Compose, API/worker use service DNS names (`postgres`,
`redis`) rather than localhost.

## Provider Configuration

  ---------------------------------------------------------------------------
  Variable                    Default                 Implemented options
  --------------------------- ----------------------- -----------------------
  `PROVIDER_DIARIZATION`      `demo`                  `demo`

  `PROVIDER_SPEECH_TO_TEXT`   `demo`                  `demo`, optional
                                                      `faster_whisper` path

  `STT_PROVIDER`              `demo`                  `demo`,
                                                      `faster_whisper`

  `PROVIDER_TRANSLATION`      `demo`                  `demo`

  `PROVIDER_TEXT_TO_SPEECH`   `demo`                  `demo`

  `PROVIDER_STORAGE`          `local`                 configuration value
                                                      present; submitted
                                                      storage implementation
                                                      is local
  ---------------------------------------------------------------------------

`STT_PROVIDER`, when set, takes precedence over
`PROVIDER_SPEECH_TO_TEXT`.

### Faster-Whisper settings

  Variable                 Default
  ------------------------ ---------
  `WHISPER_MODEL_SIZE`     `tiny`
  `WHISPER_DEVICE`         `cpu`
  `WHISPER_COMPUTE_TYPE`   `int8`

The optional dependency must be installed to use the Faster-Whisper
provider. The default Docker/demo path remains `demo` and does not
download an AI model.

## Docker Compose Provider Overrides

Compose keeps demo providers as safe defaults but allows environment
overrides.

Example:

``` bash
STT_PROVIDER=faster_whisper docker compose up --build
```

This only selects the adapter. The image/environment must also contain
the optional Faster-Whisper dependency/model requirements. The submitted
default demo does not require them.

## Upload Validation

The API performs validation before creating a queued job: 1. extension
allow-list 2. streaming upload size limit 3. `ffprobe` duration
validation 4. configured maximum duration

Invalid uploads are deleted and are not queued.

## Retry Configuration

`MAX_RETRIES` bounds explicit manual retries.

Current behavior: - only `FAILED` jobs are retryable - retry outside
`FAILED` returns HTTP 409 - exhausted retry budget returns HTTP 409 -
accepted retry clears stale error code/message - accepted retry returns
the job to the queue

The implementation does not claim automatic Celery retry.

## Storage Layout

The local storage implementation creates job-scoped locations for: -
uploads - intermediate work - outputs

Docker Compose mounts `/app/storage` as a persistent shared application
volume for API and worker containers.

In a production multi-host deployment this should be replaced with
object storage.

## Production Configuration Guidance

Do not use sample credentials in production.

Recommended production changes: - inject secrets from a secret manager -
use managed PostgreSQL and Redis - use object storage - configure
per-environment limits - configure queue-specific worker concurrency -
add authentication and rate limiting - configure centralized
logs/metrics/tracing - apply storage lifecycle/retention rules

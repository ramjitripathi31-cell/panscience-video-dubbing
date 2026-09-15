# AI-Powered Video Dubbing Platform

A production-oriented backend take-home implementation for asynchronous
multi-language video dubbing.

The service accepts a video, validates it, creates a durable processing
job, executes a staged background pipeline, persists
transcript/translation/artifact metadata, and exposes REST APIs for
status, transcripts, subtitles, dubbed-video downloads, retry, and
cancellation.

> **Important scope note:** The default repository is intentionally
> reproducible without paid AI credentials. It uses deterministic demo
> providers for diarization, translation, and text-to-speech.
> FFmpeg/ffprobe media processing, PostgreSQL persistence, Redis/Celery
> orchestration, job lifecycle, artifact generation, and the REST API
> are real. An optional Faster-Whisper STT adapter is implemented, but
> real model execution is not claimed as verified in the submitted
> environment.

## Architecture

``` mermaid
flowchart LR
    C[Client / Swagger / curl] --> API[FastAPI]
    API --> PG[(PostgreSQL)]
    API -->|enqueue| R[(Redis)]
    R --> W[Celery Worker]
    W --> PG
    W --> FF[FFmpeg / ffprobe]
    W --> P[AI Provider Layer]
    W --> S[(Storage)]
    API --> S
```

The API is the control plane; expensive processing runs in Celery
workers. PostgreSQL is the durable source of truth, Redis provides
queueing, and media/AI operations are isolated behind services/provider
contracts.

See [Architecture](docs/ARCHITECTURE.md) for the detailed flow and
diagrams.

## Capability Matrix

  -----------------------------------------------------------------------------
  Capability                Status                  Notes
  ------------------------- ----------------------- ---------------------------
  REST video upload         Implemented             streamed upload

  MP4/MOV/AVI/MKV           Implemented             WEBM also accepted
  validation                                        

  Configurable upload size  Implemented             default 500 MB

  10-minute duration limit  Implemented             ffprobe; default 600
                                                    seconds

  Background processing     Implemented             Celery + Redis

  Durable job state         Implemented             PostgreSQL

  Speaker diarization       Demo                    deterministic provider

  Timestamped STT           Demo by default         optional Faster-Whisper
                                                    adapter implemented

  Source-language detection Optional STT path       Faster-Whisper adapter

  Translation               Demo                    preserves
                                                    segment/speaker/timestamp
                                                    structure

  Multiple target languages Implemented             per-language
                            structurally            translations/artifacts

  Text-to-speech            Demo                    deterministic demo audio,
                                                    not real translated speech

  A/V muxing                Implemented             FFmpeg

  Subtitle generation       Implemented             SRT from timestamped
                                                    segments

  Transcript output         Implemented             API + artifact

  Dubbed-video artifact     Implemented demo        media artifact is
                            pipeline                generated; demo TTS is not
                                                    production dubbing

  Status/progress API       Implemented             stage + progress

  Retry failed job          Implemented             manual, bounded by
                                                    `MAX_RETRIES`

  Cancel job                Implemented             immediate for pending;
                                                    cooperative for running

  Structured logging        Implemented             application/worker logging

  Job events/audit trail    Implemented             persisted events

  Docker Compose            Implemented             API, worker, PostgreSQL,
                                                    Redis

  Automated tests           Implemented             14 passing at final
                                                    verification

  Neural lip-sync           Not implemented         production extension

  Authentication/RBAC       Not implemented         optional assignment
                                                    requirement

  Kubernetes/multi-region   Documented only         production evolution
  -----------------------------------------------------------------------------

## Technology Stack

-   Python 3.12
-   FastAPI
-   SQLAlchemy 2.x
-   Alembic
-   PostgreSQL 16
-   Redis 7
-   Celery
-   FFmpeg / ffprobe
-   Pydantic Settings
-   pytest
-   Docker / Docker Compose
-   optional Faster-Whisper STT

## Quick Start

### Prerequisites

Recommended: - Docker - Docker Compose

No paid AI API key is required for the default demo.

### 1. Configure

``` bash
cp .env.example .env
```

The sample configuration defaults to deterministic demo providers.

### 2. Start the stack

``` bash
docker compose up --build -d
```

### 3. Check health

``` bash
curl http://localhost:8000/health
```

Swagger/OpenAPI:

``` text
http://localhost:8000/docs
```

### 4. Inspect services

``` bash
docker compose ps
```

The Compose stack starts: - `api` - `worker` - `postgres` - `redis`

## REST API

  ----------------------------------------------------------------------------------------------
  Method                  Endpoint                                       Purpose
  ----------------------- ---------------------------------------------- -----------------------
  `POST`                  `/api/v1/jobs`                                 upload video and create
                                                                         dubbing job

  `GET`                   `/api/v1/jobs/{job_id}`                        job status/progress

  `GET`                   `/api/v1/jobs/{job_id}/transcript`             timestamped transcript

  `GET`                   `/api/v1/jobs/{job_id}/video/{language}`       dubbed-video artifact

  `GET`                   `/api/v1/jobs/{job_id}/subtitles/{language}`   SRT artifact

  `POST`                  `/api/v1/jobs/{job_id}/retry`                  retry eligible failed
                                                                         job

  `POST`                  `/api/v1/jobs/{job_id}/cancel`                 request cancellation

  `GET`                   `/health`                                      dependency-aware health
                                                                         check
  ----------------------------------------------------------------------------------------------

FastAPI also provides the exact request schema and response models
through Swagger.

## Example Workflow

### Create a job

``` bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -F "file=@sample.mp4" \
  -F "target_languages=hi"
```

Use the returned job ID in subsequent requests.

### Check status

``` bash
curl http://localhost:8000/api/v1/jobs/<JOB_ID>
```

### Fetch transcript

``` bash
curl http://localhost:8000/api/v1/jobs/<JOB_ID>/transcript
```

### Download subtitles

``` bash
curl -o subtitles-hi.srt \
  http://localhost:8000/api/v1/jobs/<JOB_ID>/subtitles/hi
```

### Download dubbed-video artifact

``` bash
curl -o dubbed-hi.mp4 \
  http://localhost:8000/api/v1/jobs/<JOB_ID>/video/hi
```

### Cancel

``` bash
curl -X POST http://localhost:8000/api/v1/jobs/<JOB_ID>/cancel
```

### Retry a failed job

``` bash
curl -X POST http://localhost:8000/api/v1/jobs/<JOB_ID>/retry
```

Retry is accepted only for `FAILED` jobs and is bounded by the
configured retry budget.

## Processing Pipeline

The worker exposes meaningful processing stages:

``` text
VALIDATING
  -> EXTRACTING_AUDIO
  -> DIARIZING
  -> TRANSCRIBING
  -> TRANSLATING
  -> GENERATING_AUDIO
  -> SYNCHRONIZING
  -> GENERATING_SUBTITLES
  -> COMPLETED
```

Persisted job states include:

``` text
PENDING
RUNNING
SUCCEEDED
FAILED
CANCEL_REQUESTED
CANCELLED
```

Failures are persisted with error information. Running-job cancellation
is cooperative and checked between stages.

## Provider Abstraction

The pipeline defines provider contracts for:

``` text
DiarizationProvider
SpeechToTextProvider
TranslationProvider
TextToSpeechProvider
StorageProvider
```

This prevents the orchestration layer from being tied directly to one AI
vendor.

### Default mode

``` text
diarization = demo
speech-to-text = demo
translation = demo
text-to-speech = demo
storage = local
```

This mode is deterministic and does not require external credentials.

### Optional Faster-Whisper

An optional Faster-Whisper speech-to-text adapter is available and
configured through environment variables.

Typical lightweight settings:

``` env
STT_PROVIDER=faster_whisper
WHISPER_MODEL_SIZE=tiny
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

The adapter is lazy-loaded. The normal test/demo path does not download
an AI model.

The adapter boundary is unit-tested with a fake model; real model
execution/download is not claimed as verified for this submission.

## Configuration

Important defaults include:

``` env
MAX_UPLOAD_SIZE_MB=500
MAX_DURATION_SECONDS=600
PROCESSING_TIMEOUT_SECONDS=3600
MAX_RETRIES=2
WORKER_CONCURRENCY=2

PROVIDER_DIARIZATION=demo
PROVIDER_SPEECH_TO_TEXT=demo
PROVIDER_TRANSLATION=demo
PROVIDER_TEXT_TO_SPEECH=demo
PROVIDER_STORAGE=local
```

Docker Compose keeps demo values as safe defaults while allowing
environment overrides.

See [Configuration Guide](docs/CONFIGURATION.md) for the full
explanation.

## Retry and Failure Recovery

The implementation uses explicit bounded manual retry.

A retry: - is allowed only when the job is `FAILED` - respects
`MAX_RETRIES` - clears stale error fields - requeues the job - returns
HTTP 409 when retry is not allowed

Automatic Celery retry is intentionally not claimed. A production
implementation would classify transient/permanent errors before
automatically retrying provider or infrastructure failures.

## Storage

The take-home uses job-scoped local filesystem storage shared by API and
worker containers.

This keeps Docker Compose self-contained.

For a multi-host production deployment, the intended evolution is object
storage such as: - Amazon S3 - Google Cloud Storage - Azure Blob
Storage - MinIO

Database rows should store object keys/metadata rather than media blobs.

## Testing

Run the test suite in the project environment:

``` bash
pytest
```

The final corrective verification completed with:

``` text
14 passed
```

The suite covers deterministic provider behavior, configuration,
readiness/health, models, optional Faster-Whisper adapter boundaries,
and key job API validation/lifecycle behavior.

No external model download is required by the normal test suite.

## Scaling

The design intentionally separates API traffic from media processing.

### \~5 videos

-   single API instance
-   PostgreSQL
-   Redis
-   1-2 workers
-   local/shared or object storage

### \~500 videos

-   stateless API replicas
-   managed PostgreSQL/Redis
-   multiple Celery workers
-   object storage
-   queue-depth autoscaling
-   centralized observability

### \~5,000 videos

Split processing into stage-specific queues/pools: - validation/media -
diarization/STT - translation - TTS - synchronization/muxing

CPU and GPU worker pools can then scale independently based on queue
depth, queue age, CPU/GPU utilization, provider limits, and latency.

See [Scaling and Production Evolution](docs/SCALING.md).

## Observability

Implemented: - structured logs - job status/stage/progress - persisted
job events - dependency-aware health endpoint

Production evolution: - correlation IDs - Prometheus metrics -
OpenTelemetry - centralized logs - queue-age and failure alerts -
provider latency/error/cost metrics

## Security

Implemented: - extension allow-list - streaming size validation -
duration validation - job-scoped internal paths - filename
sanitization - artifact existence checks

Production evolution: - authentication/authorization - rate
limiting/quotas - MIME/magic-byte validation - malware scanning - signed
object URLs - secret manager - encryption and retention controls

## Known Limitations

The following are deliberately explicit:

1.  Default diarization is deterministic demo behavior, not production
    speaker diarization.
2.  Default translation is deterministic demo behavior.
3.  Default TTS generates demo audio and does not synthesize the
    translated transcript as natural speech.
4.  The generated MP4 demonstrates orchestration/media muxing; it must
    not be interpreted as production-quality AI dubbing.
5.  Neural/frame-level lip-sync is not implemented.
6.  The optional Faster-Whisper adapter is implemented and unit-tested
    at its boundary, but real model execution was not verified in the
    submitted environment.
7.  Authentication/RBAC is not implemented.
8.  Local storage is suitable for the Compose demo, not horizontally
    scaled multi-host production.
9.  Automatic transient-error retry/provider fallback is not
    implemented.

These are extension points rather than hidden claims.

## Documentation

-   [Architecture](docs/ARCHITECTURE.md)
-   [Design Decisions](docs/DESIGN_DECISIONS.md)
-   [Configuration Guide](docs/CONFIGURATION.md)
-   [Scaling and Production Evolution](docs/SCALING.md)

## Repository Structure

``` text
.
├── src/app/
│   ├── api/            # REST endpoints
│   ├── db/             # SQLAlchemy models/session
│   ├── providers/      # provider contracts/adapters
│   ├── schemas/        # API schemas
│   ├── services/       # media, pipeline, storage, subtitles
│   └── workers/        # Celery app/tasks
├── alembic/            # database migrations
├── tests/              # automated tests
├── docs/               # architecture/design/config/scaling
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Design Philosophy

The submission prioritizes a clean production-oriented control plane and
an honest, reproducible end-to-end demo over pretending that lightweight
mocks provide production-quality AI dubbing.

The main architectural goals are: - keep HTTP handling separate from
expensive work - persist workflow state durably - make provider
boundaries replaceable - keep operational limits configurable - make
failure/retry/cancellation visible - keep the default evaluator setup
deterministic - provide a clear path from a single-host demo to
horizontally scaled CPU/GPU processing

# Architecture

## 1. Overview

PanScience Video Dubbing is an asynchronous video-processing service
built around a FastAPI control plane and Celery worker pipeline. The
repository is intentionally structured so that expensive media/AI work
does not execute inside HTTP request handlers.

The submitted implementation provides a deterministic end-to-end demo
pipeline, real FFmpeg/ffprobe media processing, PostgreSQL persistence,
Redis/Celery background execution, downloadable artifacts, cancellation,
bounded manual retry, and configurable provider contracts. An optional
`faster-whisper` speech-to-text adapter is implemented, but real model
execution is not required for the default demo.

The default diarization, translation, and text-to-speech providers are
deterministic demo providers. They must not be interpreted as production
AI voice cloning or neural dubbing.

## 2. System Architecture

``` mermaid
flowchart LR
    C[Client / Swagger / curl] -->|REST| API[FastAPI API]
    API -->|job metadata| PG[(PostgreSQL)]
    API -->|enqueue job| R[(Redis)]
    R --> W[Celery Worker]
    W -->|read/update state| PG
    W --> FF[FFmpeg / ffprobe]
    W --> DP[Diarization Provider]
    W --> STT[Speech-to-Text Provider]
    W --> TR[Translation Provider]
    W --> TTS[Text-to-Speech Provider]
    W --> FS[(Storage)]
    API -->|download artifacts| FS
```

### Component responsibilities

**FastAPI API** - Accepts video uploads and target languages. -
Validates file extension, upload size, and video duration. - Creates and
persists jobs. - Enqueues background processing. - Exposes status,
transcript, subtitle, dubbed-video, retry, and cancel endpoints.

**PostgreSQL** - Source of truth for job state and processing
metadata. - Persists jobs, transcript segments, translations, artifacts,
and job events. - Allows API and worker processes to coordinate without
relying on in-memory state.

**Redis + Celery** - Redis is the Celery broker/result backend in the
submitted Docker setup. - Celery separates long-running media work from
HTTP request handling. - Worker concurrency is configurable. - Failed
jobs can be manually retried subject to the configured retry budget.

**FFmpeg / ffprobe** - `ffprobe` validates video duration. - FFmpeg
extracts source audio. - FFmpeg creates deterministic demo audio through
the demo TTS path. - FFmpeg muxes generated audio with the source
video. - This is real media processing even when the selected AI
providers are demo implementations.

**Provider layer** - `DiarizationProvider` - `SpeechToTextProvider` -
`TranslationProvider` - `TextToSpeechProvider` - `StorageProvider`

The interfaces isolate the pipeline from provider-specific
implementations. Provider selection is configuration-driven where
implemented.

**Storage** - The submitted implementation uses local filesystem storage
behind a storage contract. - Uploads, intermediate work files, and final
artifacts are separated by job. - A production deployment can replace
local storage with S3, GCS, Azure Blob, or MinIO without changing the
public API.

## 3. Request and Processing Flow

``` mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Queue as Redis/Celery
    participant Worker
    participant Media as FFmpeg/Providers
    participant Storage

    Client->>API: POST /api/v1/jobs
    API->>Storage: stream uploaded video
    API->>Media: ffprobe duration
    API->>DB: create PENDING job
    API->>Queue: enqueue job_id
    API-->>Client: 202 QUEUED

    Queue->>Worker: process job
    Worker->>DB: RUNNING + stage/progress
    Worker->>Media: extract audio
    Worker->>Media: diarize
    Worker->>Media: transcribe
    Worker->>DB: persist transcript
    Worker->>Media: translate per language
    Worker->>DB: persist translations
    Worker->>Media: generate demo audio
    Worker->>Media: mux audio/video
    Worker->>Storage: write MP4/SRT/transcript
    Worker->>DB: persist artifacts + SUCCEEDED

    Client->>API: GET status/artifacts
    API->>DB: resolve metadata
    API->>Storage: resolve artifact
    API-->>Client: JSON/FileResponse
```

## 4. Pipeline State Model

The worker reports the following processing stages:

1.  `VALIDATING`
2.  `EXTRACTING_AUDIO`
3.  `DIARIZING`
4.  `TRANSCRIBING`
5.  `TRANSLATING`
6.  `GENERATING_AUDIO`
7.  `SYNCHRONIZING`
8.  `GENERATING_SUBTITLES`
9.  `COMPLETED`

Persisted job states are: - `PENDING` - `RUNNING` - `SUCCEEDED` -
`FAILED` - `CANCEL_REQUESTED` - `CANCELLED`

Cancellation is cooperative. A running job is moved to
`CANCEL_REQUESTED`, and the worker checks for cancellation between
stages before moving it to `CANCELLED`.

## 5. Data Model

### Job

Stores: - ID - state - current stage - progress - target languages -
attempt count - input path - error information - lifecycle timestamps

### TranscriptSegment

Stores: - job ID - speaker ID - start/end timestamps - source text

### Translation

Stores: - job ID - language - source segment relationship - translated
text

### Artifact

Stores: - job ID - artifact type - language when applicable - storage
path

### JobEvent

Stores lifecycle/audit events such as creation, stage transitions,
retry, cancellation, failure, and completion.

## 6. AI and Media Abstraction

The pipeline depends on provider contracts instead of directly coupling
every stage to a vendor SDK.

Default assignment mode: - Diarization: deterministic demo - STT:
deterministic demo - Translation: deterministic demo - TTS:
deterministic demo - Storage: local

Optional STT: - `faster-whisper` - lazy-loaded - configurable model
size/device/compute type - intended for local CPU execution with `tiny`,
`cpu`, `int8` defaults when enabled

The optional Faster-Whisper adapter is implemented and unit-tested
through a fake model boundary, but a real model download/execution is
not claimed as verified in the submitted environment.

## 7. Synchronization Strategy

The implementation preserves segment timestamps in
transcript/translation data and generates subtitles from those
timestamps.

The current demo media path generates a duration-matched demo audio
track and muxes it with the source video using FFmpeg. This validates
the orchestration and artifact pipeline, but it is not neural lip-sync
and the demo TTS output is not genuine translated speech.

A production implementation would synthesize speech per translated
segment, measure the generated duration, apply bounded
time-stretching/padding, place each speaker segment on the original
timeline, mix speaker tracks, and then mux the result with the video.
Neural lip-sync would be a separate optional GPU stage.

## 8. Failure Recovery

-   Exceptions during pipeline execution are persisted as `FAILED`.
-   Error code and error message are stored on the job.
-   A job event is written for failure.
-   The API exposes a manual retry endpoint.
-   Retry is allowed only for `FAILED` jobs.
-   Retry is bounded by `MAX_RETRIES`.
-   Accepted retries clear stale error information and enqueue the job
    again.
-   Automatic Celery retry is intentionally not claimed.

## 9. Observability

Implemented: - structured application logging - persisted job state -
stage/progress tracking - job events - dependency-aware `/health`

Production extension: - correlation/request IDs - Prometheus metrics -
OpenTelemetry traces - centralized logs - queue depth/latency
dashboards - provider latency/error/cost metrics - alerts on failure
rate, queue age, worker saturation, and storage errors

## 10. Security Boundaries

Implemented: - extension allow-list - streaming upload size
enforcement - ffprobe duration validation - internal UUID-based job
paths - sanitized storage filenames - artifact existence checks

Production extension: - authenticated upload/download -
authorization/RBAC - rate limiting - MIME/magic-byte validation -
malware scanning - signed object-store URLs - secret manager -
encryption policies and retention/deletion controls

## 11. Deployment Topology

The submitted Docker Compose stack contains: - API - worker - PostgreSQL
16 - Redis 7 - persistent volumes for PostgreSQL, Redis, and application
storage

The API applies Alembic migrations before startup. API and worker share
the storage volume in the local Compose topology.

For production, local shared storage would be replaced by object storage
and API/worker replicas would become stateless.

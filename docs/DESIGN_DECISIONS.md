# Design Decisions

## 1. FastAPI for the API Layer

FastAPI was selected because the assignment is API-first and benefits
from typed request/response models, automatic OpenAPI/Swagger
documentation, dependency injection, and straightforward file-upload
handling.

A separate frontend was intentionally not added. Swagger and REST
endpoints are sufficient to demonstrate the required workflow and keep
the submission focused on backend architecture and media processing.

## 2. Asynchronous Processing with Celery and Redis

Video processing can take much longer than an HTTP request should remain
open. The API therefore performs only admission work---upload,
validation, persistence, and enqueueing---and delegates processing to
Celery.

Redis is used as the Celery broker/result backend in the submitted
environment.

Benefits: - HTTP workers are not blocked by FFmpeg/AI work. - processing
concurrency can be configured independently. - worker processes can
scale separately from API processes. - failure state is persisted in
PostgreSQL. - the architecture naturally evolves to multiple worker
pools.

## 3. PostgreSQL as the Source of Truth

Redis is not used as the authoritative job database. PostgreSQL persists
durable workflow state and artifacts metadata.

This provides: - durable job status - transcript/translation
persistence - artifact discovery - retry/cancellation state - audit/job
events - future reporting and operational queries

Alembic is used for schema migrations.

## 4. Provider Contracts Instead of Vendor Coupling

The code defines contracts for diarization, speech-to-text, translation,
text-to-speech, and storage.

The purpose is to keep orchestration stable while provider
implementations change. For example, a production STT adapter can be
replaced without rewriting the job API or database workflow.

The submission does not claim that every provider has multiple
production implementations. The abstraction is present, while the
default diarization, translation, and TTS implementations are
deterministic demo providers.

## 5. Deterministic Demo Providers

The take-home assignment has a short delivery window and production AI
dubbing involves large models, credentials, GPU/CPU cost, and
provider-specific operational concerns.

The default system therefore uses deterministic demo providers so
that: - Docker startup is reproducible. - the end-to-end pipeline can be
demonstrated without paid credentials. - tests do not depend on external
APIs. - evaluator setup remains lightweight. - provider boundaries and
workflow architecture remain visible.

Trade-off: demo diarization/translation/TTS do not prove
production-quality voice preservation or real translated speech. This
limitation is explicit rather than hidden.

## 6. Optional Faster-Whisper STT

A local Faster-Whisper adapter was added as an optional STT path.

Configuration supports: - model size - device - compute type

The intended lightweight configuration is `tiny` + `cpu` + `int8`.

The adapter is lazy-loaded so the default demo does not require the
dependency or model. Unit tests verify the adapter boundary with a fake
model. Real model execution/download is not claimed as verified for the
submitted environment.

## 7. FFmpeg as the Media Primitive

FFmpeg/ffprobe were chosen because they are mature, widely deployed
primitives for: - media metadata inspection - audio extraction -
audio/video muxing - deterministic media generation

This avoids implementing codec/container logic in application code.

## 8. Configuration-Driven Limits

Operational constraints are settings rather than hard-coded workflow
rules.

Examples: - allowed extensions - maximum upload size - maximum
duration - processing timeout - retry budget - worker concurrency -
provider selections - storage root

The default duration is 600 seconds, matching the assignment's 10-minute
requirement.

## 9. Manual Bounded Retry

The public API provides explicit retry for failed jobs.

Retry is: - restricted to `FAILED` - bounded by `MAX_RETRIES` - rejected
with HTTP 409 when invalid - responsible for clearing stale error fields
before requeueing

A complex automatic retry framework was intentionally not added.
Automatic retries need error classification and idempotency rules;
blindly retrying deterministic validation or provider errors can
increase load without improving reliability.

A production implementation would classify errors into transient and
permanent categories and automatically retry only transient failures
with exponential backoff/jitter.

## 10. Cooperative Cancellation

Forcefully terminating FFmpeg/model processes can leave partial
artifacts or inconsistent state. The current worker checks cancellation
at stage boundaries.

This provides a simple and predictable state transition:
`RUNNING -> CANCEL_REQUESTED -> CANCELLED`.

Production evolution can add process-level cancellation for long-running
stages while preserving cleanup/idempotency rules.

## 11. Local Storage Behind an Abstraction

Local filesystem storage keeps Docker Compose self-contained.

The storage contract exists so production deployments can move to object
storage. This is important because a shared local volume does not scale
cleanly across independent hosts.

Production target: - object storage for uploads/intermediates/outputs -
database stores object keys/metadata - signed URLs for upload/download -
lifecycle policies for cleanup

## 12. No Authentication in the Take-Home

Authentication is optional in the assignment. It was intentionally
omitted to prioritize the core processing architecture, API lifecycle,
tests, and deployment.

Production would add: - authenticated users/service clients - job
ownership - authorization on status/download/retry/cancel - rate
limiting/quotas - signed artifact access

## 13. No Neural Lip-Sync in the Demo

The current synchronization path is timestamp/subtitle-aware and uses
FFmpeg muxing, but does not implement a neural lip-sync model.

Production-quality lip-sync would be an optional GPU-intensive stage and
should not be placed on the same generic worker pool as lightweight
metadata/API work.

This is documented as a future extension rather than represented as
implemented functionality.

## 14. Testing Strategy

The suite focuses on deterministic behavior and boundaries: -
configuration - health/readiness - demo pipeline utilities - model
defaults - optional Faster-Whisper adapter boundary - upload/API
validation - status/cancel/retry rules - artifact behavior

External model downloads are deliberately excluded from the normal test
suite.

## 15. Key Trade-Off Summary

  -----------------------------------------------------------------------
  Decision                Benefit                 Trade-off
  ----------------------- ----------------------- -----------------------
  FastAPI                 typed API + OpenAPI     backend-only demo

  Celery + Redis          independent background  additional
                          workers                 infrastructure

  PostgreSQL              durable workflow state  DB dependency

  Demo AI providers       reproducible/no paid    not production AI
                          credentials             quality

  Optional Faster-Whisper real STT integration    runtime model not
                          path                    verified

  Local storage           simple Compose setup    not multi-host scalable

  Manual retry            explicit/predictable    no automatic transient
                                                  recovery

  Cooperative             simple state safety     not immediate mid-stage
  cancellation                                    termination

  FFmpeg                  reliable media          external binary/process
                          operations              boundary
  -----------------------------------------------------------------------

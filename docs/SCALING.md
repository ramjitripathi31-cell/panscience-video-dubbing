# Scaling and Production Evolution

The submitted Docker Compose topology is designed for a take-home
demonstration. The architecture separates API, durable state, queueing,
processing, and storage so each concern can evolve independently.

## 1. Approximately 5 Videos

A small deployment can use:

``` text
1 API instance
1 PostgreSQL instance
1 Redis instance
1-2 Celery workers
Object storage or a shared persistent volume
```

At this scale: - one queue is sufficient - worker concurrency can be
low - PostgreSQL stores job state - Redis buffers processing work -
vertical scaling is acceptable - local/shared storage can work for a
controlled environment

The submitted Compose topology is closest to this tier.

## 2. Approximately 500 Videos

Move from a single-host topology to horizontally scalable services:

``` text
Load Balancer
    |
API replicas
    |
PostgreSQL (managed)
Redis (managed)
    |
Celery worker replicas
    |
Object Storage
```

Changes: - multiple stateless API replicas - multiple worker replicas -
managed PostgreSQL with backups - managed Redis - S3/GCS/Azure
Blob/MinIO instead of local storage - autoscaling based on queue
depth/queue age - signed artifact URLs - centralized
logging/metrics/tracing - provider rate-limit handling - idempotent
stage execution - automatic retry only for classified transient failures

API scaling and worker scaling should be independent.

## 3. Approximately 5,000 Videos

A single generic worker queue becomes inefficient because stages have
different resource profiles.

Recommended production pipeline:

``` mermaid
flowchart LR
    U[Upload/API] --> Q1[Validation Queue]
    Q1 --> CPU1[Media Workers]
    CPU1 --> Q2[Diarization/STT Queue]
    Q2 --> AI1[CPU/GPU STT Workers]
    AI1 --> Q3[Translation Queue]
    Q3 --> AI2[Translation Workers/Provider]
    AI2 --> Q4[TTS Queue]
    Q4 --> GPU[TTS / GPU Workers]
    GPU --> Q5[Mux/Subtitles Queue]
    Q5 --> CPU2[FFmpeg Workers]
    CPU2 --> OBJ[(Object Storage)]
    U --> DB[(PostgreSQL)]
```

### Stage-specific queues

Examples: - validation/media metadata - audio extraction -
diarization/STT - translation - TTS - synchronization/muxing - artifact
finalization

This prevents a slow GPU/TTS stage from starving lightweight work.

### Autoscaling signals

Scale workers using: - queue depth - oldest-message age - processing
latency - CPU utilization - GPU utilization - provider rate limits -
failure rate

Kubernetes HPA/KEDA, ECS service autoscaling, or equivalent can
implement these policies.

## 4. Storage Evolution

### Demo

Docker volume/local filesystem.

### Production

Object storage.

Recommended object-key model:

``` text
jobs/{job_id}/input/source.mp4
jobs/{job_id}/work/source.wav
jobs/{job_id}/outputs/{language}/dubbed.mp4
jobs/{job_id}/outputs/{language}/subtitles.srt
jobs/{job_id}/outputs/transcript.txt
```

Benefits: - workers do not require shared host disks - artifacts survive
worker replacement - signed URLs reduce API bandwidth - lifecycle rules
can delete intermediates automatically - multi-region replication
becomes possible later

## 5. Database Scaling

PostgreSQL remains the source of truth.

At higher scale: - index job state/timestamps and artifact lookups - use
connection pooling - keep large media outside the database - use read
replicas for reporting if needed - archive old job events - define
retention policies - use managed backups/PITR

## 6. Reliability

### Idempotency

Each stage should be safe to rerun or should detect an already-completed
artifact.

### Retry classification

Production errors should be classified.

Transient examples: - provider 429/5xx - temporary network failure -
object-store timeout

Permanent examples: - corrupt/unsupported media - invalid request -
unsupported language/provider capability

Transient failures can use exponential backoff with jitter. Permanent
failures should fail immediately.

### Dead-letter handling

Jobs that exhaust automatic transient retries should move to a
dead-letter/manual-review path rather than loop indefinitely.

## 7. Provider Capacity and Cost

At high volume, provider abstraction becomes operationally important.

Production routing can consider: - language support - latency -
quality - price - regional availability - rate limits - GPU availability

A provider fallback layer can be added without changing the public API,
but it is not implemented in the submitted demo.

## 8. Observability at Scale

Recommended metrics: - uploads accepted/rejected - queue depth and
oldest-job age - jobs completed/failed/cancelled - stage duration
percentiles - total processing latency - provider latency/error rate -
FFmpeg failure rate - CPU/GPU utilization - artifact-storage failures -
cost per processed minute

Recommended tracing:
`request_id -> job_id -> queue task -> processing stage -> provider call -> artifact`

## 9. Security at Scale

Add: - authentication and job ownership - RBAC/service accounts - rate
limiting and quotas - MIME/magic-byte validation - malware scanning -
signed object URLs - encryption in transit/at rest - secret manager -
audit logging - configurable retention/deletion - tenant isolation if
exposed as SaaS

## 10. Multi-Region Evolution

Multi-region is not necessary for the take-home implementation.

If required: - regional API/worker stacks - region-local queues -
replicated/global object storage - database strategy based on
consistency requirements - route uploads to the closest region - keep
job processing within one region when possible - avoid cross-region
transfer of large media unless required

## 11. Summary

  --------------------------------------------------------------------------------------
  Load           API            Queue/Workers    Storage               Operations
  -------------- -------------- ---------------- --------------------- -----------------
  \~5 videos     1 API          1 queue, 1-2     local/shared/object   basic health/logs
                                workers                                

  \~500 videos   API replicas   worker replicas  object storage        autoscaling +
                                                                       managed
                                                                       DB/Redis +
                                                                       metrics

  \~5,000 videos stateless API  stage-specific   object storage        queue-based
                 fleet          CPU/GPU pools                          autoscaling,
                                                                       tracing, DLQ,
                                                                       cost/rate-limit
                                                                       routing
  --------------------------------------------------------------------------------------

The core design principle is to scale processing capacity independently
from the REST API and to keep PostgreSQL/object storage as durable
sources of state and artifacts.

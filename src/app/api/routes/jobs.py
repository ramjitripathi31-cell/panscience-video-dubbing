import json
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Artifact, Job, JobEvent, JobStatus, TranscriptSegment, Translation
from app.db.session import get_db
from app.providers.factory import get_diarization_provider
from app.schemas.jobs import JobCreated, JobResponse, TranscriptResponse
from app.services.media import probe_duration
from app.services.storage import LocalStorage

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

def _langs(raw: str) -> list[str]:
    try: value = json.loads(raw)
    except json.JSONDecodeError: value = [x.strip() for x in raw.split(",")]
    if isinstance(value, str): value = [value]
    if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x.strip() or len(x) > 16 for x in value): raise HTTPException(422, "target_languages must be a non-empty language list")
    return list(dict.fromkeys(x.strip().lower() for x in value))

@router.post("", response_model=JobCreated, status_code=202)
async def create_job(video: UploadFile = File(...), target_languages: str = Form(...), db: Session = Depends(get_db)):
    suffix = Path(video.filename or "").suffix.lower()
    if suffix not in settings.allowed_extensions: raise HTTPException(415, "unsupported video extension")
    job_id = uuid.uuid4(); storage = LocalStorage(); path = storage.upload_path(str(job_id), f"input{suffix}"); total = 0
    with path.open("wb") as output:
        while chunk := await video.read(1024 * 1024):
            total += len(chunk)
            if total > settings.max_upload_size_mb * 1024 * 1024: path.unlink(missing_ok=True); raise HTTPException(413, "upload exceeds configured max size")
            output.write(chunk)
    try: duration = probe_duration(path)
    except Exception: path.unlink(missing_ok=True); raise HTTPException(422, "unable to validate video duration")
    if duration > settings.max_duration_seconds: path.unlink(missing_ok=True); raise HTTPException(422, "video duration exceeds configured maximum")
    job = Job(id=job_id, status=JobStatus.PENDING, input_path=str(path), target_languages=_langs(target_languages)); db.add(job); db.add(JobEvent(job_id=job_id, event_type="created")); db.commit()
    from app.workers.tasks import process_job_task
    process_job_task.delay(str(job_id))
    return JobCreated(id=job_id, status="QUEUED")

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job: raise HTTPException(404, "job not found")
    return job

def _job(db, job_id):
    job = db.get(Job, job_id)
    if not job: raise HTTPException(404, "job not found")
    return job

@router.post("/{job_id}/retry", response_model=JobCreated)
def retry_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = _job(db, job_id)
    if job.status != JobStatus.FAILED: raise HTTPException(409, "only failed jobs can be retried")
    job.status, job.current_stage, job.progress, job.error_code, job.error_message = JobStatus.PENDING, None, 0, None, None; db.add(JobEvent(job_id=job.id, event_type="retry")); db.commit()
    from app.workers.tasks import process_job_task
    process_job_task.delay(str(job.id)); return JobCreated(id=job.id, status="QUEUED")

@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = _job(db, job_id)
    if job.status == JobStatus.PENDING: job.status, job.current_stage = JobStatus.CANCELLED, "CANCELLED"
    elif job.status == JobStatus.RUNNING: job.status = JobStatus.CANCEL_REQUESTED
    else: raise HTTPException(409, "job cannot be cancelled in its current state")
    db.add(JobEvent(job_id=job.id, event_type="cancel_requested")); db.commit(); return job

def _artifact(db, job_id, kind, language=None):
    query = select(Artifact).where(Artifact.job_id == job_id, Artifact.artifact_type == kind)
    if language: query = query.where(Artifact.language == language)
    artifact = db.scalar(query)
    if not artifact or not Path(artifact.path).is_file(): raise HTTPException(404, "artifact unavailable")
    return artifact

@router.get("/{job_id}/transcript", response_model=TranscriptResponse)
def transcript(job_id: uuid.UUID, db: Session = Depends(get_db)):
    _job(db, job_id); rows = db.scalars(select(TranscriptSegment).where(TranscriptSegment.job_id == job_id).order_by(TranscriptSegment.start_time)).all()
    if not rows: raise HTTPException(404, "transcript unavailable")
    return {"segments": [{"speaker_id": r.speaker_id, "start_time": r.start_time, "end_time": r.end_time, "source_text": r.source_text} for r in rows]}

@router.get("/{job_id}/subtitles/{language}")
def subtitles(job_id: uuid.UUID, language: str, db: Session = Depends(get_db)): return FileResponse(_artifact(db, job_id, "subtitle", language).path, media_type="application/x-subrip", filename=f"subtitles_{language}.srt")

@router.get("/{job_id}/video/{language}")
def video(job_id: uuid.UUID, language: str, db: Session = Depends(get_db)): return FileResponse(_artifact(db, job_id, "video", language).path, media_type="video/mp4", filename=f"dubbed_{language}.mp4")


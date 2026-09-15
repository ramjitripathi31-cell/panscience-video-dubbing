"""Deterministic asynchronous demo pipeline; no AI or neural media processing."""
from pathlib import Path
import logging
import shutil

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Artifact, Job, JobEvent, JobStatus, TranscriptSegment, Translation
from app.providers.contracts import DemoSegment
from app.providers.factory import get_diarization_provider, get_speech_to_text_provider, get_text_to_speech_provider, get_translation_provider
from app.services.media import build_demo_audio, extract_audio, mux_audio, probe_duration
from app.services.storage import LocalStorage
from app.services.subtitles import to_srt

logger = logging.getLogger(__name__)
STAGES = [("VALIDATING", 5), ("EXTRACTING_AUDIO", 15), ("DIARIZING", 25), ("TRANSCRIBING", 40), ("TRANSLATING", 55), ("GENERATING_AUDIO", 70), ("SYNCHRONIZING", 82), ("GENERATING_SUBTITLES", 95)]


class CancelledPipeline(Exception): pass


def _event(db: Session, job: Job, event_type: str, message: str | None = None) -> None:
    db.add(JobEvent(job_id=job.id, event_type=event_type, message=message))


def _stage(db: Session, job: Job, stage: str, progress: int) -> None:
    db.refresh(job)
    if job.status in (JobStatus.CANCEL_REQUESTED, JobStatus.CANCELLED): raise CancelledPipeline()
    job.status, job.current_stage, job.progress = JobStatus.RUNNING, stage, progress
    _event(db, job, "stage", stage)
    db.commit()


def process_job(job_id: str) -> None:
    from app.db.session import SessionLocal
    db = SessionLocal(); storage = LocalStorage()
    try:
        job = db.get(Job, job_id)
        if not job or job.status in (JobStatus.CANCELLED, JobStatus.CANCEL_REQUESTED): return
        job.attempt_count += 1; job.started_at = job.started_at or __import__("datetime").datetime.now(__import__("datetime").timezone.utc); job.error_code = job.error_message = None; db.commit()
        upload = Path(job.input_path)
        _stage(db, job, "VALIDATING", 5); probe_duration(upload)
        audio = storage.work_path(str(job.id), "source.wav")
        _stage(db, job, "EXTRACTING_AUDIO", 15); extract_audio(upload, audio)
        _stage(db, job, "DIARIZING", 25); segments = get_diarization_provider().diarize(audio)
        _stage(db, job, "TRANSCRIBING", 40); segments = get_speech_to_text_provider().transcribe(audio, segments)
        db.execute(delete(TranscriptSegment).where(TranscriptSegment.job_id == job.id)); db.commit()
        segment_rows = []
        for segment in segments:
            row = TranscriptSegment(job_id=job.id, speaker_id=segment.speaker_id, start_time=segment.start_time, end_time=segment.end_time, source_text=segment.source_text); db.add(row); segment_rows.append(row)
        db.commit()
        _stage(db, job, "TRANSLATING", 55); translator = get_translation_provider(); translations = {}
        db.execute(delete(Translation).where(Translation.job_id == job.id))
        for language in job.target_languages:
            translations[language] = [translator.translate(s.source_text, language) for s in segments]
            for row, text in zip(segment_rows, translations[language]): db.add(Translation(job_id=job.id, language=language, segment_id=row.id, translated_text=text))
        db.commit()
        _stage(db, job, "GENERATING_AUDIO", 70); duration = probe_duration(upload); tts = get_text_to_speech_provider()
        _stage(db, job, "SYNCHRONIZING", 82)
        db.execute(delete(Artifact).where(Artifact.job_id == job.id)); db.commit()
        for language in job.target_languages:
            wav = storage.work_path(str(job.id), f"{language}.wav"); build_demo_audio(upload, wav, tts, language, duration)
            video = storage.output_path(str(job.id), f"dubbed_{language}.mp4"); mux_audio(upload, wav, video)
            db.add(Artifact(job_id=job.id, language=language, artifact_type="video", path=str(video)))
        _stage(db, job, "GENERATING_SUBTITLES", 95)
        for language in job.target_languages:
            srt = storage.output_path(str(job.id), f"subtitles_{language}.srt"); srt.write_text(to_srt(segments, {i: translations[language][i] for i in range(len(segments))}), encoding="utf-8")
            db.add(Artifact(job_id=job.id, language=language, artifact_type="subtitle", path=str(srt)))
        db.add(Artifact(job_id=job.id, artifact_type="transcript", path=str(storage.output_path(str(job.id), "transcript.txt"))))
        storage.output_path(str(job.id), "transcript.txt").write_text("\n".join(f"{s.speaker_id}: {s.source_text}" for s in segments), encoding="utf-8")
        job.status, job.current_stage, job.progress, job.completed_at = JobStatus.SUCCEEDED, "COMPLETED", 100, __import__("datetime").datetime.now(__import__("datetime").timezone.utc); _event(db, job, "completed"); db.commit()
    except CancelledPipeline:
        job = db.get(Job, job_id); job.status, job.current_stage = JobStatus.CANCELLED, "CANCELLED"; _event(db, job, "cancelled"); db.commit()
    except Exception as exc:
        logger.exception("demo_pipeline_failed", extra={"job_id": str(job_id)})
        job = db.get(Job, job_id); job.status, job.error_code, job.error_message = JobStatus.FAILED, type(exc).__name__.upper(), str(exc)[:2000]; _event(db, job, "failed", str(exc)); db.commit()
    finally: db.close()


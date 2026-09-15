import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, Integer, String, Text, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_jobs_progress"),
        CheckConstraint("attempt_count >= 0", name="ck_jobs_attempt_count"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", values_callable=lambda values: [v.value for v in values]),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    )
    current_stage: Mapped[str | None] = mapped_column(String(100))
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_languages: Mapped[list[str]] = mapped_column(ARRAY(String(16)), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    input_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    speaker_id: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)


class Translation(Base):
    __tablename__ = "translations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    segment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("transcript_segments.id", ondelete="CASCADE"))
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)


class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    language: Mapped[str | None] = mapped_column(String(16))
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JobEvent(Base):
    __tablename__ = "job_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

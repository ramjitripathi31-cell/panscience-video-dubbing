from celery import Celery

from app.config import settings

celery_app = Celery(
    "panscience_video_dubbing",
    broker=settings.broker_url,
    backend=settings.result_backend,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_concurrency=settings.worker_concurrency,
    task_time_limit=settings.processing_timeout_seconds,
    timezone="UTC",
)

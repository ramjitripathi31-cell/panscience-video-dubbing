from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.healthcheck")
def healthcheck() -> str:
    return "ok"


@celery_app.task(name="app.workers.process_job")
def process_job_task(job_id: str) -> None:
    from app.services.pipeline import process_job
    process_job(job_id)

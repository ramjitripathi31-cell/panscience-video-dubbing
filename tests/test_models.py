from app.db.models import Job, JobStatus


def test_job_defaults() -> None:
    job = Job(input_path="/uploads/video.mp4", target_languages=["hi", "ta"])
    assert job.status is None or job.status == JobStatus.PENDING
    assert job.input_path == "/uploads/video.mp4"
    assert job.target_languages == ["hi", "ta"]


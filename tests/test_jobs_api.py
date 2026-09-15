import uuid

from fastapi.testclient import TestClient

from app.api.routes.jobs import router
from app.config import settings
from app.db.models import Job, JobStatus
from app.db.session import get_db
from app.main import app


class FakeDB:
    def __init__(self, job=None):
        self.job = job
        self.added = []

    def add(self, value):
        self.added.append(value)

    def commit(self):
        return None

    def get(self, model, job_id):
        return self.job if self.job and self.job.id == job_id else None

    def scalar(self, query):
        return None


def _client(db):
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_create_job_upload(monkeypatch, tmp_path):
    db = FakeDB()
    monkeypatch.setattr("app.api.routes.jobs.LocalStorage", lambda: __import__("app.services.storage", fromlist=["LocalStorage"]).LocalStorage(str(tmp_path)))
    monkeypatch.setattr("app.api.routes.jobs.probe_duration", lambda path: 4.0)
    monkeypatch.setattr("app.workers.tasks.process_job_task.delay", lambda job_id: None)
    response = _client(db).post("/api/v1/jobs", files={"video": ("clip.mp4", b"video", "video/mp4")}, data={"target_languages": '["hi"]'})
    app.dependency_overrides.clear()
    assert response.status_code == 202
    assert response.json()["status"] == "QUEUED"
    assert any(isinstance(value, Job) for value in db.added)


def test_create_rejects_extension_and_size(monkeypatch, tmp_path):
    db = FakeDB()
    monkeypatch.setattr("app.api.routes.jobs.LocalStorage", lambda: __import__("app.services.storage", fromlist=["LocalStorage"]).LocalStorage(str(tmp_path)))
    client = _client(db)
    assert client.post("/api/v1/jobs", files={"video": ("clip.txt", b"x", "text/plain")}, data={"target_languages": "hi"}).status_code == 415
    monkeypatch.setattr(settings, "max_upload_size_mb", 0)
    assert client.post("/api/v1/jobs", files={"video": ("clip.mp4", b"x", "video/mp4")}, data={"target_languages": "hi"}).status_code == 413
    app.dependency_overrides.clear()


def test_create_rejects_duration(monkeypatch, tmp_path):
    db = FakeDB()
    monkeypatch.setattr("app.api.routes.jobs.LocalStorage", lambda: __import__("app.services.storage", fromlist=["LocalStorage"]).LocalStorage(str(tmp_path)))
    monkeypatch.setattr("app.api.routes.jobs.probe_duration", lambda path: 601.0)
    response = _client(db).post("/api/v1/jobs", files={"video": ("clip.mp4", b"x", "video/mp4")}, data={"target_languages": "hi"})
    app.dependency_overrides.clear()
    assert response.status_code == 422


def test_status_cancel_retry_rules(monkeypatch):
    job = Job(id=uuid.uuid4(), status=JobStatus.FAILED, input_path="/tmp/input.mp4", target_languages=["hi"], attempt_count=1, progress=0)
    db = FakeDB(job)
    monkeypatch.setattr("app.workers.tasks.process_job_task.delay", lambda job_id: None)
    client = _client(db)
    assert client.get(f"/api/v1/jobs/{job.id}").status_code == 200
    retry = client.post(f"/api/v1/jobs/{job.id}/retry")
    assert retry.status_code == 200 and job.status == JobStatus.PENDING
    job.status, job.attempt_count = JobStatus.FAILED, settings.max_retries
    assert client.post(f"/api/v1/jobs/{job.id}/retry").status_code == 409
    job.status = JobStatus.PENDING
    assert client.post(f"/api/v1/jobs/{job.id}/cancel").status_code == 200
    assert job.status == JobStatus.CANCELLED
    app.dependency_overrides.clear()


def test_artifact_unavailable_returns_404():
    job = Job(id=uuid.uuid4(), status=JobStatus.SUCCEEDED, input_path="/tmp/input.mp4", target_languages=["hi"], progress=100, attempt_count=1)
    client = _client(FakeDB(job))
    response = client.get(f"/api/v1/jobs/{job.id}/video/hi")
    app.dependency_overrides.clear()
    assert response.status_code == 404

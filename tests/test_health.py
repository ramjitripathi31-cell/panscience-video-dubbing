from fastapi.testclient import TestClient

from app.main import app
from app.services import readiness


client = TestClient(app)


def test_health_ready(monkeypatch) -> None:
    monkeypatch.setattr(readiness, "database_ready", lambda: True)
    monkeypatch.setattr(readiness, "redis_ready", lambda: True)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "ok", "database": "ok", "redis": "ok"}


def test_health_not_ready(monkeypatch) -> None:
    monkeypatch.setattr(readiness, "database_ready", lambda: False)
    monkeypatch.setattr(readiness, "redis_ready", lambda: True)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["database"] == "error"


from pathlib import Path
import uuid

from app.config import settings


class LocalStorage:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.storage_root).resolve()
        for name in ("uploads", "work", "outputs"):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def _path(self, area: str, job_id: str, filename: str) -> Path:
        safe_job = uuid.UUID(str(job_id))
        safe_name = Path(filename).name
        path = (self.root / area / str(safe_job) / safe_name).resolve()
        base = (self.root / area).resolve()
        if base not in path.parents: raise ValueError("unsafe storage path")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def upload_path(self, job_id: str, filename: str) -> Path: return self._path("uploads", job_id, filename)
    def work_path(self, job_id: str, filename: str) -> Path: return self._path("work", job_id, filename)
    def output_path(self, job_id: str, filename: str) -> Path: return self._path("outputs", job_id, filename)


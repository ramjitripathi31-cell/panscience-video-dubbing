from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class JobCreated(BaseModel): id: UUID; status: str
class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; status: str; current_stage: str | None; progress: int; attempt_count: int; target_languages: list[str]; error_code: str | None; error_message: str | None; created_at: datetime | None; updated_at: datetime | None; started_at: datetime | None; completed_at: datetime | None; attempts: int | None = None

    def model_post_init(self, __context) -> None:
        if self.attempts is None:
            self.attempts = self.attempt_count
class TranscriptResponse(BaseModel): segments: list[dict[str, Any]]

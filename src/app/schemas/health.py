from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok", "not_ready"]
    app: Literal["ok"] = "ok"
    database: Literal["ok", "error"]
    redis: Literal["ok", "error"]


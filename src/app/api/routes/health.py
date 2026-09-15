import asyncio
import logging

from fastapi import APIRouter, Response, status

from app.schemas.health import HealthResponse
from app.services import readiness

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


async def _probe(probe) -> bool:
    try:
        return await asyncio.to_thread(probe)
    except Exception:
        logger.exception("readiness_probe_failed", extra={"probe": probe.__name__})
        return False


@router.get("/health", response_model=HealthResponse)
async def health(response: Response) -> HealthResponse:
    database_ok, redis_ok = await asyncio.gather(
        _probe(readiness.database_ready), _probe(readiness.redis_ready)
    )
    ready = database_ok and redis_ok
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ok" if ready else "not_ready",
        database="ok" if database_ok else "error",
        redis="ok" if redis_ok else "error",
    )


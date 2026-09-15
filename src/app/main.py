from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
from app.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)


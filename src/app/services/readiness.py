from redis import Redis
from sqlalchemy import text

from app.config import settings
from app.db.session import engine


def database_ready() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def redis_ready() -> bool:
    client = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
    try:
        return bool(client.ping())
    finally:
        client.close()


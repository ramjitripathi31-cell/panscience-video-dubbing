from app.config import Settings


def test_celery_urls_default_to_redis() -> None:
    config = Settings(_env_file=None, redis_url="redis://example:6379/4")
    assert config.broker_url == "redis://example:6379/4"
    assert config.result_backend == "redis://example:6379/4"


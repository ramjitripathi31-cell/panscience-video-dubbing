from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "PanScience Video Dubbing"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = Field(
        default="postgresql+psycopg://panscience:panscience@localhost:5432/panscience"
    )
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    allowed_extensions: list[str] = [".mp4", ".mov", ".mkv", ".webm", ".avi"]
    max_upload_size_mb: int = 500
    max_duration_seconds: int = 600
    processing_timeout_seconds: int = 3600
    max_retries: int = 2
    worker_concurrency: int = 2
    provider_diarization: str = "demo"
    provider_speech_to_text: str = "demo"
    stt_provider: str | None = None
    whisper_model_size: str = "tiny"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    provider_translation: str = "demo"
    provider_text_to_speech: str = "demo"
    provider_storage: str = "local"
    storage_root: str = "./storage"

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def selected_stt_provider(self) -> str:
        return self.stt_provider or self.provider_speech_to_text


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

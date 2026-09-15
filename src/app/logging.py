import logging
import logging.config

from app.config import settings


def configure_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                    "rename_fields": {"levelname": "level", "asctime": "timestamp"},
                    "reserved_attrs": [],
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {"handlers": ["default"], "level": settings.log_level.upper()},
            "loggers": {
                "uvicorn.access": {"handlers": ["default"], "propagate": False},
                "uvicorn.error": {"handlers": ["default"], "propagate": False},
            },
        }
    )

"""Optional local faster-whisper STT provider. This is not a demo provider.

The dependency and model are both optional: importing the application in demo mode
does not import faster-whisper or download a model. The model is loaded on first use.
"""
from pathlib import Path
from typing import Any

from app.config import settings
from app.providers.contracts import DemoSegment


class FasterWhisperSpeechToTextProvider:
    def __init__(self, model: Any | None = None) -> None:
        self._model = model
        self.source_language: str | None = None

    @property
    def model(self) -> Any:
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError(
                    "faster-whisper is not installed; install the whisper extra to use STT_PROVIDER=faster_whisper"
                ) from exc
            self._model = WhisperModel(
                settings.whisper_model_size,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )
        return self._model

    def transcribe(self, audio_path: Path, segments: list[DemoSegment]) -> list[DemoSegment]:
        detected_segments, info = self.model.transcribe(str(audio_path))
        self.source_language = getattr(info, "language", None)
        return [
            DemoSegment(
                speaker_id=f"speaker_{index + 1}",
                start_time=float(segment.start),
                end_time=float(segment.end),
                source_text=str(segment.text).strip(),
                source_language=self.source_language,
            )
            for index, segment in enumerate(detected_segments)
        ]

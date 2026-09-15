from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class DemoSegment:
    speaker_id: str
    start_time: float
    end_time: float
    source_text: str


class DiarizationProvider(Protocol):
    def diarize(self, audio_path: Path) -> list[DemoSegment]: ...


class SpeechToTextProvider(Protocol):
    def transcribe(self, audio_path: Path, segments: list[DemoSegment]) -> list[DemoSegment]: ...


class TranslationProvider(Protocol):
    def translate(self, text: str, target_language: str) -> str: ...


class TextToSpeechProvider(Protocol):
    def synthesize(self, text: str, target_language: str, output_path: Path, duration: float) -> None: ...


class StorageProvider(Protocol):
    def upload_path(self, job_id: str, filename: str) -> Path: ...
    def work_path(self, job_id: str, filename: str) -> Path: ...
    def output_path(self, job_id: str, filename: str) -> Path: ...


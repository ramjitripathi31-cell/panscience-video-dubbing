"""Deterministic DEMO providers for tests and local development; not AI integrations."""
from pathlib import Path
import subprocess

from app.providers.contracts import DemoSegment


class DemoDiarizationProvider:
    def diarize(self, audio_path: Path) -> list[DemoSegment]:
        return [DemoSegment("speaker_1", 0.0, 2.0, "demo speech one"), DemoSegment("speaker_2", 2.0, 4.0, "demo speech two")]


class DemoSpeechToTextProvider:
    def transcribe(self, audio_path: Path, segments: list[DemoSegment]) -> list[DemoSegment]:
        return segments


class DemoTranslationProvider:
    def translate(self, text: str, target_language: str) -> str:
        return f"[{target_language}] {text}"


class DemoTextToSpeechProvider:
    def synthesize(self, text: str, target_language: str, output_path: Path, duration: float) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", str(max(duration, 0.1)), "-c:a", "pcm_s16le", str(output_path)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )


from pathlib import Path
from types import SimpleNamespace

from app.config import Settings
from app.providers.contracts import DemoSegment
from app.providers.factory import get_speech_to_text_provider
from app.providers.faster_whisper import FasterWhisperSpeechToTextProvider


def test_provider_selection(monkeypatch) -> None:
    monkeypatch.setattr("app.providers.factory.settings", Settings(_env_file=None, stt_provider="demo"))
    assert type(get_speech_to_text_provider()).__name__ == "DemoSpeechToTextProvider"
    monkeypatch.setattr("app.providers.factory.settings", Settings(_env_file=None, stt_provider="faster_whisper"))
    assert type(get_speech_to_text_provider()).__name__ == "FasterWhisperSpeechToTextProvider"


def test_faster_whisper_mapping_and_language() -> None:
    class FakeModel:
        def transcribe(self, path):
            return [SimpleNamespace(start=0.25, end=1.5, text=" hello ")], SimpleNamespace(language="es")

    provider = FasterWhisperSpeechToTextProvider(model=FakeModel())
    result = provider.transcribe(Path("audio.wav"), [])
    assert result == [DemoSegment("speaker_1", 0.25, 1.5, "hello", "es")]
    assert provider.source_language == "es"


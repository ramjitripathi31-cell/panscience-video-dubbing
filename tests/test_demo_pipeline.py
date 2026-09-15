from pathlib import Path

from app.providers.demo import DemoDiarizationProvider, DemoTranslationProvider
from app.services.storage import LocalStorage
from app.services.subtitles import to_srt


def test_demo_provider_is_deterministic() -> None:
    segments = DemoDiarizationProvider().diarize(Path("ignored.wav"))
    assert [(s.speaker_id, s.start_time, s.end_time, s.source_text) for s in segments] == [
        ("speaker_1", 0.0, 2.0, "demo speech one"),
        ("speaker_2", 2.0, 4.0, "demo speech two"),
    ]
    assert DemoTranslationProvider().translate("hello", "hi") == "[hi] hello"


def test_srt_generation() -> None:
    segments = DemoDiarizationProvider().diarize(Path("ignored.wav"))
    output = to_srt(segments, {0: "[hi] demo speech one", 1: "[hi] demo speech two"})
    assert "00:00:00,000 --> 00:00:02,000" in output
    assert "[hi] demo speech two" in output


def test_storage_rejects_path_traversal(tmp_path) -> None:
    storage = LocalStorage(str(tmp_path))
    safe = storage.output_path("00000000-0000-0000-0000-000000000001", "../out.mp4")
    assert safe.name == "out.mp4"

from app.providers.contracts import DemoSegment


def _stamp(seconds: float) -> str:
    millis = int(round(seconds * 1000)); h, millis = divmod(millis, 3600000); m, millis = divmod(millis, 60000); s, ms = divmod(millis, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def to_srt(segments: list[DemoSegment], translated: dict[int, str] | None = None) -> str:
    lines = []
    for index, segment in enumerate(segments):
        text = translated.get(index, segment.source_text) if translated else segment.source_text
        lines.extend([str(index + 1), f"{_stamp(segment.start_time)} --> {_stamp(segment.end_time)}", text, ""])
    return "\n".join(lines)


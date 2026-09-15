from pathlib import Path
import subprocess


def probe_duration(path: Path) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def extract_audio(video: Path, audio: Path) -> None:
    audio.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(audio)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def mux_audio(video: Path, audio: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-shortest", str(output)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def build_demo_audio(video: Path, output: Path, tts_provider, language: str, duration: float) -> None:
    # Deterministic demo timeline: one silent segment per synthesized transcript chunk.
    tts_provider.synthesize("demo timeline", language, output, duration)


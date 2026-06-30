"""Input validation helpers."""
from __future__ import annotations

from pathlib import Path


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def validate_inputs(script: Path, voice: Path, movie: Path) -> None:
    """Validate user-selected script, voice-over, and movie files."""
    if not script.is_file() or script.suffix.lower() != ".txt":
        raise ValueError("Kịch bản phải là file .txt có tồn tại.")
    if not voice.is_file() or voice.suffix.lower() not in AUDIO_EXTENSIONS:
        raise ValueError("Voice phải là file âm thanh hợp lệ (mp3, wav, m4a, ...).")
    if not movie.is_file() or movie.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError("Video phim phải là file video hợp lệ (mp4, mov, mkv, ...).")
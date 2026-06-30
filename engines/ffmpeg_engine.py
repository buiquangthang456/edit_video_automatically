"""FFmpeg media processing engine."""
from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable, Iterable
from pathlib import Path

from models.segment import Segment
from utils.text import escape_drawtext, shorten_caption


class FFmpegEngine:
    """Small wrapper around FFmpeg/FFprobe commands used by the editor."""

    def __init__(
        self,
        ffmpeg_bin: str = "ffmpeg",
        ffprobe_bin: str = "ffprobe",
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.ffmpeg_bin = ffmpeg_bin
        self.ffprobe_bin = ffprobe_bin
        self.logger = logger or print

    def require_tools(self) -> None:
        """Ensure FFmpeg and FFprobe are available in PATH."""
        self._require_tool(self.ffmpeg_bin)
        self._require_tool(self.ffprobe_bin)

    def duration(self, path: Path) -> float:
        """Return media duration in seconds using FFprobe."""
        self._require_tool(self.ffprobe_bin)
        command = [
            self.ffprobe_bin,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ]
        result = subprocess.run(command, capture_output=True, check=True, text=True)
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

    def build_clip(self, movie: Path, segment: Segment, clip_path: Path, resolution: str) -> None:
        """Render a transformed silent clip for one timeline segment."""
        video_filter = ",".join(
            [
                f"scale={resolution}:force_original_aspect_ratio=increase",
                f"crop={resolution}",
                "eq=contrast=1.06:saturation=0.92",
                self._subtitle_filter(segment.text),
            ]
        )
        self._run(
            [
                self.ffmpeg_bin,
                "-y",
                "-ss",
                f"{segment.source_start:.3f}",
                "-i",
                str(movie),
                "-t",
                f"{segment.duration:.3f}",
                "-an",
                "-vf",
                video_filter,
                "-r",
                "30",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                str(clip_path),
            ]
        )

    def concat_clips(self, clips: Iterable[Path], output: Path) -> None:
        """Concatenate rendered clips into one silent video."""
        list_file = output.with_suffix(".concat.txt")
        list_file.write_text(
            "".join(f"file '{clip.as_posix()}'\n" for clip in clips),
            encoding="utf-8",
        )
        self._run(
            [
                self.ffmpeg_bin,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(output),
            ]
        )

    def add_voice(self, video: Path, voice: Path, output: Path) -> None:
        """Attach the provided voice-over as the final audio track."""
        self._run(
            [
                self.ffmpeg_bin,
                "-y",
                "-i",
                str(video),
                "-i",
                str(voice),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-shortest",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output),
            ]
        )

    def _subtitle_filter(self, text: str) -> str:
        caption = escape_drawtext(shorten_caption(text))
        return (
            "drawtext="
            f"text='{caption}':"
            "fontcolor=white:fontsize=38:line_spacing=10:"
            "box=1:boxcolor=black@0.62:boxborderw=20:"
            "x=(w-text_w)/2:y=h-text_h-70"
        )

    def _run(self, command: list[str]) -> None:
        self._log("\n$ " + " ".join(command))
        completed = subprocess.run(command, text=True)
        if completed.returncode != 0:
            raise RuntimeError(
                f"Lệnh thất bại với mã {completed.returncode}: {' '.join(command)}"
            )

    def _log(self, message: str) -> None:
        self.logger(message)

    @staticmethod
    def _require_tool(name: str) -> None:
        if shutil.which(name) is None:
            raise RuntimeError(f"Không tìm thấy {name}. Hãy cài FFmpeg và thêm vào PATH.")
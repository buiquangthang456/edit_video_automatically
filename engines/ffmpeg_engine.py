"""FFmpeg media processing engine."""
from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable, Iterable
from pathlib import Path

from models.segment import Segment
from utils.text import escape_drawtext, wrap_caption


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

    def has_audio_stream(self, path: Path) -> bool:
        """Return True when the media file contains at least one audio stream."""
        self._require_tool(self.ffprobe_bin)
        command = [
            self.ffprobe_bin,
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index",
            "-of",
            "json",
            str(path),
        ]
        result = subprocess.run(command, capture_output=True, check=True, text=True)
        data = json.loads(result.stdout)
        return bool(data.get("streams"))

    def build_clip(self, movie: Path, segment: Segment, clip_path: Path, resolution: str) -> None:
        """Render a transformed silent clip for one timeline segment."""
        caption_width, font_size, line_spacing, bottom_margin = self._caption_layout(resolution)
        caption_path = clip_path.with_suffix(".caption.txt")
        caption_path.write_text(
            wrap_caption(segment.text, caption_width),
            encoding="utf-8",
        )
        video_filter = ",".join(
            [
                f"scale={resolution}:force_original_aspect_ratio=increase",
                f"crop={resolution}",
                "eq=contrast=1.06:saturation=0.92",
                self._subtitle_filter(
                    caption_path,
                    font_size=font_size,
                    line_spacing=line_spacing,
                    bottom_margin=bottom_margin,
                ),
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
        """Replace any video audio with the provided voice-over track."""
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
                "-af",
                "asetpts=PTS-STARTPTS,aresample=async=1:first_pts=0,volume=1.25,apad",
                "-shortest",
                "-map_metadata",
                "-1",
                "-map_chapters",
                "-1",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-disposition:a:0",
                "default",
                "-movflags",
                "+faststart",
                str(output),
            ]
        )
        if not self.has_audio_stream(output):
            raise RuntimeError("Video xuất ra không có audio. Hãy kiểm tra lại file voice-over đầu vào.")

    def _subtitle_filter(
        self,
        caption_path: Path,
        font_size: int,
        line_spacing: int,
        bottom_margin: int,
    ) -> str:
        caption_file = escape_drawtext(caption_path.resolve().as_posix())
        return (
            "drawtext="
            f"textfile='{caption_file}':reload=0:"
            f"fontcolor=white:fontsize={font_size}:line_spacing={line_spacing}:"
            "box=1:boxcolor=black@0.62:boxborderw=20:"
            f"x=(w-text_w)/2:y=h-text_h-{bottom_margin}:fix_bounds=1"
        )

    @staticmethod
    def _caption_layout(resolution: str) -> tuple[int, int, int, int]:
        """Return wrapping and sizing values that keep captions inside the frame."""
        try:
            frame_width, frame_height = (int(value) for value in resolution.split(":", 1))
        except (TypeError, ValueError):
            frame_width, frame_height = 1080, 1920

        font_size = max(26, min(48, round(frame_width / 28)))
        horizontal_padding = max(80, round(frame_width * 0.08))
        usable_width = max(200, frame_width - horizontal_padding * 2)
        caption_width = max(20, int(usable_width / (font_size * 0.58)))
        line_spacing = max(6, round(font_size * 0.24))
        bottom_margin = max(50, round(frame_height * 0.055))
        return caption_width, font_size, line_spacing, bottom_margin

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

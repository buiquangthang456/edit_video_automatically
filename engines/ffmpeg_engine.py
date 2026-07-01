"""FFmpeg media processing engine."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable, Iterable
from pathlib import Path

from models.segment import Segment
from models.subtitle import SubtitleCue
from utils.text import escape_ass


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

    def has_audible_audio(self, path: Path, silence_threshold_db: float = -60.0) -> bool:
        """Return True when the first audio stream contains a non-silent signal."""
        self._require_tool(self.ffmpeg_bin)
        command = [
            self.ffmpeg_bin,
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-af",
            "volumedetect",
            "-f",
            "null",
            os.devnull,
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(f"Không thể kiểm tra âm lượng của file: {path}")

        match = re.search(
            r"max_volume:\s*(?P<peak>-?inf|[-+]?\d+(?:\.\d+)?)\s*dB",
            completed.stderr,
            flags=re.IGNORECASE,
        )
        if match is None:
            raise RuntimeError(f"FFmpeg không trả về mức âm lượng của file: {path}")
        peak = match.group("peak").lower()
        peak_db = float("-inf") if peak == "-inf" else float(peak)
        return peak_db > silence_threshold_db

    def voice_pause_boundaries(self, path: Path) -> list[float]:
        """Return the midpoint of natural pauses detected in a voice track."""
        command = [
            self.ffmpeg_bin,
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-vn",
            "-af",
            "silencedetect=noise=-38dB:d=0.28",
            "-f",
            "null",
            os.devnull,
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            self._log("Không thể dò khoảng nghỉ của voice; dùng timeline ước lượng theo văn bản.")
            return []

        event_pattern = re.compile(
            r"silence_(?P<kind>start|end):\s*(?P<time>[-+]?\d+(?:\.\d+)?)"
        )
        pauses: list[float] = []
        current_start: float | None = None
        for match in event_pattern.finditer(completed.stderr):
            timestamp = float(match.group("time"))
            if match.group("kind") == "start":
                current_start = timestamp
            elif current_start is not None and timestamp > current_start:
                pauses.append((current_start + timestamp) / 2.0)
                current_start = None
        return pauses

    def subtitle_cues(self, path: Path) -> list[SubtitleCue]:
        """Extract the preferred embedded text subtitle track, if one exists."""
        probe_command = [
            self.ffprobe_bin,
            "-v",
            "error",
            "-select_streams",
            "s",
            "-show_entries",
            "stream=index,codec_name:stream_tags=language,title",
            "-of",
            "json",
            str(path),
        ]
        probed = subprocess.run(probe_command, capture_output=True, text=True)
        if probed.returncode != 0:
            return []
        streams = json.loads(probed.stdout or "{}").get("streams", [])
        text_codecs = {"ass", "ssa", "subrip", "srt", "webvtt", "mov_text"}
        streams = [stream for stream in streams if stream.get("codec_name") in text_codecs]
        if not streams:
            return []

        def subtitle_priority(stream: dict[str, object]) -> tuple[int, int]:
            tags = stream.get("tags") if isinstance(stream.get("tags"), dict) else {}
            language = str(tags.get("language", "")).casefold()
            if language in {"vie", "vi", "vietnamese"}:
                return (0, int(stream["index"]))
            if language in {"eng", "en", "english"}:
                return (1, int(stream["index"]))
            return (2, int(stream["index"]))

        selected = min(streams, key=subtitle_priority)
        extract_command = [
            self.ffmpeg_bin,
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            f"0:{selected['index']}",
            "-c:s",
            "ass",
            "-f",
            "ass",
            "pipe:1",
        ]
        extracted = subprocess.run(extract_command, capture_output=True)
        if extracted.returncode != 0:
            return []
        document = extracted.stdout.decode("utf-8-sig", errors="replace")
        return self._parse_ass_cues(document)

    def keyframe_times(self, path: Path) -> list[float]:
        """Return video packet keyframe timestamps without decoding the movie."""
        command = [
            self.ffprobe_bin,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_packets",
            "-show_entries",
            "packet=pts_time,flags",
            "-of",
            "csv=p=0",
            str(path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            return []
        keyframes: list[float] = []
        for line in completed.stdout.splitlines():
            fields = [field.strip() for field in line.split(",")]
            if len(fields) >= 2 and "K" in fields[-1]:
                try:
                    keyframes.append(float(fields[0]))
                except ValueError:
                    continue
        return keyframes

    def build_clip(self, movie: Path, segment: Segment, clip_path: Path, resolution: str) -> None:
        """Render a transformed silent clip for one timeline segment."""
        width, height = self._parse_resolution(resolution)
        subtitle_path = clip_path.with_suffix(".subtitle.ass")
        self._write_subtitle_file(subtitle_path, segment.text, width, height)
        video_filter = ",".join(
            [
                f"scale={resolution}:force_original_aspect_ratio=increase",
                f"crop={resolution}",
                "eq=contrast=1.06:saturation=0.92",
                self._subtitle_filter(subtitle_path),
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

    def add_voice(
        self,
        video: Path,
        voice: Path,
        output: Path,
        target_duration: float | None = None,
    ) -> None:
        """Replace any video audio with the provided voice-over track."""
        command = [
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
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-c:v",
            "copy",
            "-filter:a",
            (
                "asetpts=PTS-STARTPTS,"
                "aresample=48000:async=1:first_pts=0,"
                "loudnorm=I=-16:TP=-1.5:LRA=11,"
                "apad"
            ),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-metadata:s:a:0",
            "language=vie",
            "-disposition:a:0",
            "default",
            "-movflags",
            "+faststart",
        ]
        if target_duration is not None:
            command.extend(["-t", f"{target_duration:.3f}"])
        command.append(str(output))
        self._run(command)
        if not self.has_audio_stream(output):
            raise RuntimeError("Video xuất ra không có audio. Hãy kiểm tra lại file voice-over đầu vào.")
        if not self.has_audible_audio(output):
            raise RuntimeError("Audio trong video xuất ra đang im lặng. Hãy kiểm tra file voice-over đầu vào.")

    def _write_subtitle_file(self, path: Path, text: str, width: int, height: int) -> None:
        """Write a resolution-aware ASS caption that wraps inside safe margins."""
        base_size = min(width, height)
        font_size = max(24, round(base_size * 38 / 720))
        horizontal_margin = max(round(width * 0.06), font_size)
        vertical_margin = max(round(base_size * 0.08), font_size)
        box_padding = max(8, round(font_size * 0.42))
        caption = escape_ass(text)
        document = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial,{font_size},&H00FFFFFF,&H00FFFFFF,&H60000000,&H60000000,0,0,0,0,100,100,0,0,3,{box_padding},0,2,{horizontal_margin},{horizontal_margin},{vertical_margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,9:59:59.99,Caption,,0,0,0,,{caption}
"""
        path.write_text(document, encoding="utf-8-sig")

    def _subtitle_filter(self, subtitle_path: Path) -> str:
        escaped_path = self._escape_filter_path(subtitle_path)
        return f"subtitles=filename='{escaped_path}'"

    @classmethod
    def _parse_ass_cues(cls, document: str) -> list[SubtitleCue]:
        cues: list[SubtitleCue] = []
        for line in document.splitlines():
            if not line.startswith("Dialogue:"):
                continue
            fields = line.removeprefix("Dialogue:").lstrip().split(",", 9)
            if len(fields) != 10:
                continue
            _, start_text, end_text, style, name, *_margins, text = fields
            if any(marker in style.casefold() for marker in ("sign", "song", "kara", "op_", "ed_")):
                continue
            try:
                start = cls._parse_ass_timestamp(start_text)
                end = cls._parse_ass_timestamp(end_text)
            except ValueError:
                continue
            clean_text = re.sub(r"\{[^}]*}", "", text)
            clean_text = clean_text.replace(r"\N", " ").replace(r"\n", " ").strip()
            speaker = name.strip()
            searchable_text = f"{speaker} {clean_text}".strip()
            if searchable_text:
                cues.append(SubtitleCue(start=start, end=end, text=searchable_text))
        return sorted(cues, key=lambda cue: (cue.start, cue.end))

    @staticmethod
    def _parse_ass_timestamp(value: str) -> float:
        hours, minutes, seconds = value.strip().split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)

    @staticmethod
    def _escape_filter_path(path: Path) -> str:
        """Escape an absolute path for use in an FFmpeg filter option."""
        return (
            path.resolve()
            .as_posix()
            .replace("\\", r"\\")
            .replace(":", r"\:")
            .replace("'", r"\'")
            .replace(",", r"\,")
            .replace("[", r"\[")
            .replace("]", r"\]")
            .replace(";", r"\;")
        )

    @staticmethod
    def _parse_resolution(resolution: str) -> tuple[int, int]:
        """Parse an FFmpeg width:height string and reject invalid dimensions."""
        try:
            width_text, height_text = resolution.split(":")
            width, height = int(width_text), int(height_text)
        except (TypeError, ValueError) as exc:
            raise ValueError("Tỉ lệ xuất phải có dạng rộng:cao, ví dụ 1280:720.") from exc
        if width <= 0 or height <= 0:
            raise ValueError("Chiều rộng và chiều cao video phải lớn hơn 0.")
        return width, height

    def _run(self, command: list[str]) -> None:
        self._log("\n$ " + " ".join(command))
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            details = completed.stderr.strip()[-4000:]
            raise RuntimeError(
                f"Lệnh thất bại với mã {completed.returncode}: {' '.join(command)}\n{details}"
            )

    def _log(self, message: str) -> None:
        self.logger(message)

    @staticmethod
    def _require_tool(name: str) -> None:
        if shutil.which(name) is None:
            raise RuntimeError(f"Không tìm thấy {name}. Hãy cài FFmpeg và thêm vào PATH.")

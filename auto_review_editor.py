"""Auto edit a movie-review style video from a script, voice-over, and source movie.

This tool intentionally focuses on review-friendly transformations (short sampled clips,
subtitles, voice-over, optional crop/zoom) but it cannot guarantee YouTube copyright
clearance or Content ID avoidance. Use only content you have rights to use, or content
that fits fair-use/fair-dealing rules in your jurisdiction.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


@dataclass(frozen=True)
class Segment:
    index: int
    text: str
    start: float
    end: float
    source_start: float

    @property
    def duration(self) -> float:
        return max(0.1, self.end - self.start)


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Không tìm thấy {name}. Hãy cài FFmpeg và thêm vào PATH.")


def run_command(command: list[str]) -> None:
    print("\n$ " + " ".join(command))
    completed = subprocess.run(command, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"Lệnh thất bại với mã {completed.returncode}: {' '.join(command)}")


def ffprobe_duration(path: Path) -> float:
    require_tool("ffprobe")
    command = [
        "ffprobe",
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


def read_script(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        raise ValueError("File kịch bản đang trống.")

    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    if len(blocks) == 1:
        # Fall back to wrapped sentence-like chunks for scripts without blank lines.
        blocks = textwrap.wrap(text.replace("\n", " "), width=180, break_long_words=False)
    return blocks


def make_segments(script_blocks: list[str], voice_duration: float, movie_duration: float) -> list[Segment]:
    total_chars = sum(max(1, len(block)) for block in script_blocks)
    cursor = 0.0
    usable_movie_duration = max(1.0, movie_duration - 8.0)
    step = usable_movie_duration / max(1, len(script_blocks))
    segments: list[Segment] = []

    for index, block in enumerate(script_blocks, start=1):
        share = max(1, len(block)) / total_chars
        duration = max(2.0, voice_duration * share)
        end = voice_duration if index == len(script_blocks) else min(voice_duration, cursor + duration)
        source_start = min(max(0.0, (index - 1) * step), max(0.0, movie_duration - (end - cursor) - 1.0))
        segments.append(Segment(index=index, text=block, start=cursor, end=end, source_start=source_start))
        cursor = end

    if segments and segments[-1].end < voice_duration:
        last = segments[-1]
        segments[-1] = Segment(last.index, last.text, last.start, voice_duration, last.source_start)
    return segments


def escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace("\n", " ")
    )


def subtitle_filter(text: str) -> str:
    caption = escape_drawtext(textwrap.shorten(text, width=130, placeholder="..."))
    return (
        "drawtext="
        f"text='{caption}':"
        "fontcolor=white:fontsize=38:line_spacing=10:"
        "box=1:boxcolor=black@0.62:boxborderw=20:"
        "x=(w-text_w)/2:y=h-text_h-70"
    )


def build_clip(movie: Path, segment: Segment, clip_path: Path, resolution: str) -> None:
    # Mild crop/zoom/contrast and subtitles create a commentary layout, not a copyright bypass.
    video_filter = ",".join(
        [
            f"scale={resolution}:force_original_aspect_ratio=increase",
            f"crop={resolution}",
            "eq=contrast=1.06:saturation=0.92",
            subtitle_filter(segment.text),
        ]
    )
    run_command(
        [
            "ffmpeg",
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


def concat_clips(clips: Iterable[Path], output: Path) -> None:
    list_file = output.with_suffix(".concat.txt")
    list_file.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips), encoding="utf-8")
    run_command(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output)])


def add_voice(video: Path, voice: Path, output: Path) -> None:
    run_command(
        [
            "ffmpeg",
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


def validate_inputs(script: Path, voice: Path, movie: Path) -> None:
    if not script.is_file() or script.suffix.lower() != ".txt":
        raise ValueError("Kịch bản phải là file .txt có tồn tại.")
    if not voice.is_file() or voice.suffix.lower() not in AUDIO_EXTENSIONS:
        raise ValueError("Voice phải là file âm thanh hợp lệ (mp3, wav, m4a, ...).")
    if not movie.is_file() or movie.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError("Video phim phải là file video hợp lệ (mp4, mov, mkv, ...).")


def edit_review(script: Path, voice: Path, movie: Path, output: Path, resolution: str) -> None:
    require_tool("ffmpeg")
    validate_inputs(script, voice, movie)
    output.parent.mkdir(parents=True, exist_ok=True)

    script_blocks = read_script(script)
    voice_duration = ffprobe_duration(voice)
    movie_duration = ffprobe_duration(movie)
    segments = make_segments(script_blocks, voice_duration, movie_duration)

    print(f"Tạo {len(segments)} đoạn clip theo kịch bản ({voice_duration:.1f}s voice-over).")
    with tempfile.TemporaryDirectory(prefix="auto-review-editor-") as temp_dir:
        temp_path = Path(temp_dir)
        clips: list[Path] = []
        for segment in segments:
            clip_path = temp_path / f"clip_{segment.index:03d}.mp4"
            build_clip(movie, segment, clip_path, resolution)
            clips.append(clip_path)

        silent_video = temp_path / "silent_review.mp4"
        concat_clips(clips, silent_video)
        add_voice(silent_video, voice, output)

    print(f"\nHoàn tất: {output}")
    print("Lưu ý: Không có công cụ nào bảo đảm tránh bản quyền/Content ID. Hãy dùng clip ngắn, thêm bình luận thật sự, và kiểm tra luật fair use.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tự dựng video review từ kịch bản, voice-over và video phim.")
    parser.add_argument("--script", required=True, type=Path, help="File .txt chứa kịch bản review")
    parser.add_argument("--voice", required=True, type=Path, help="File voice-over đã tạo sẵn")
    parser.add_argument("--movie", required=True, type=Path, help="File video phim nguồn")
    parser.add_argument("--output", default=Path("outputs/review_video.mp4"), type=Path, help="File video xuất ra")
    parser.add_argument("--resolution", default="1080:1920", help="Kích thước xuất, ví dụ 1080:1920 hoặc 1920:1080")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    edit_review(args.script, args.voice, args.movie, args.output, args.resolution)


if __name__ == "__main__":
    main()
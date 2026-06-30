"""High-level video review rendering workflow."""
from __future__ import annotations

import tempfile
from pathlib import Path

from core.segmentation import make_segments
from engines.ffmpeg_engine import FFmpegEngine
from models.config import RenderConfig
from utils.text import read_script
from utils.validation import validate_inputs


class VideoProcessor:
    """Orchestrates script parsing, segmentation, rendering, and audio mapping."""

    def __init__(self, engine: FFmpegEngine | None = None) -> None:
        self.engine = engine or FFmpegEngine()

    def render(self, config: RenderConfig) -> None:
        """Render the final review video for the provided config."""
        self.engine.require_tools()
        validate_inputs(config.script, config.voice, config.movie)
        config.output.parent.mkdir(parents=True, exist_ok=True)

        script_blocks = read_script(config.script)
        voice_duration = self.engine.duration(config.voice)
        movie_duration = self.engine.duration(config.movie)
        segments = make_segments(script_blocks, voice_duration, movie_duration)

        print(f"Tạo {len(segments)} đoạn clip theo kịch bản ({voice_duration:.1f}s voice-over).")
        with tempfile.TemporaryDirectory(prefix="auto-review-editor-") as temp_dir:
            temp_path = Path(temp_dir)
            clips: list[Path] = []
            for segment in segments:
                clip_path = temp_path / f"clip_{segment.index:03d}.mp4"
                self.engine.build_clip(config.movie, segment, clip_path, config.resolution)
                clips.append(clip_path)

            silent_video = temp_path / "silent_review.mp4"
            self.engine.concat_clips(clips, silent_video)
            self.engine.add_voice(silent_video, config.voice, config.output)

        print(f"\nHoàn tất: {config.output}")
        print(
            "Lưu ý: Không có công cụ nào bảo đảm tránh bản quyền/Content ID. "
            "Hãy dùng clip ngắn, thêm bình luận thật sự, và kiểm tra luật fair use."
        )
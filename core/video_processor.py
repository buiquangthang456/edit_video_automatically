"""High-level video review rendering workflow."""
from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path

from core.alignment import align_segments_to_subtitles
from core.segmentation import make_segments
from engines.ffmpeg_engine import FFmpegEngine
from models.config import RenderConfig
from utils.text import read_script_sections
from utils.validation import validate_inputs


class VideoProcessor:
    """Orchestrates script parsing, segmentation, rendering, and audio mapping."""

    def __init__(
        self,
        engine: FFmpegEngine | None = None,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.logger = logger or print
        self.engine = engine or FFmpegEngine(logger=self.logger)

    def render(self, config: RenderConfig) -> None:
        """Render the final review video for the provided config."""
        self.engine.require_tools()
        validate_inputs(config.script, config.voice, config.movie)
        config.output.parent.mkdir(parents=True, exist_ok=True)

        script_sections = read_script_sections(config.script)
        script_blocks = [caption for section in script_sections for caption in section]
        if not self.engine.has_audio_stream(config.voice):
            raise ValueError("File voice-over không có audio stream. Hãy chọn đúng file âm thanh.")
        if not self.engine.has_audible_audio(config.voice):
            raise ValueError("File voice-over không có tiếng hoặc âm lượng quá nhỏ. Hãy kiểm tra lại file âm thanh.")

        voice_duration = self.engine.duration(config.voice)
        movie_duration = self.engine.duration(config.movie)
        pause_boundaries = self.engine.voice_pause_boundaries(config.voice)
        segments = make_segments(
            script_blocks,
            voice_duration,
            movie_duration,
            voice_boundaries=pause_boundaries,
        )

        subtitle_cues = self.engine.subtitle_cues(config.movie)
        if subtitle_cues:
            self._log(
                f"Tìm thấy {len(subtitle_cues)} câu thoại trong video nguồn; "
                "đang căn cảnh theo nội dung kịch bản."
            )
            keyframes = self.engine.keyframe_times(config.movie)
            segments = align_segments_to_subtitles(
                segments,
                subtitle_cues,
                movie_duration,
                keyframes,
            )
        else:
            self._log(
                "Video nguồn không có phụ đề chữ phù hợp; "
                "dùng thứ tự thời gian của video để chọn cảnh."
            )

        self._log(
            f"Tạo {len(segments)} đoạn clip theo câu và {len(pause_boundaries)} khoảng nghỉ "
            f"của voice-over ({voice_duration:.1f}s)."
        )
        with tempfile.TemporaryDirectory(prefix="auto-review-editor-") as temp_dir:
            temp_path = Path(temp_dir)
            clips: list[Path] = []
            for segment in segments:
                self._log(
                    f"Dựng cảnh {segment.index}/{len(segments)} "
                    f"(voice {segment.start:.1f}-{segment.end:.1f}s, "
                    f"nguồn {segment.source_start:.1f}s)."
                )
                clip_path = temp_path / f"clip_{segment.index:03d}.mp4"
                self.engine.build_clip(config.movie, segment, clip_path, config.resolution)
                clips.append(clip_path)

            silent_video = temp_path / "silent_review.mp4"
            self.engine.concat_clips(clips, silent_video)
            self.engine.add_voice(
                silent_video,
                config.voice,
                config.output,
                target_duration=voice_duration,
            )

        self._log(f"\nHoàn tất: {config.output}")
        self._log(
            "Lưu ý: Không có công cụ nào bảo đảm tránh bản quyền/Content ID. "
            "Hãy dùng clip ngắn, thêm bình luận thật sự, và kiểm tra luật fair use."
        )

    def _log(self, message: str) -> None:
        self.logger(message)

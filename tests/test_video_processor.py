import tempfile
import unittest
from pathlib import Path

from core.video_processor import VideoProcessor
from models.config import RenderConfig


class FakeEngine:
    def __init__(self):
        self.calls = []

    def require_tools(self):
        self.calls.append(("require_tools",))

    def has_audio_stream(self, path):
        self.calls.append(("has_audio_stream", path.name))
        return True

    def has_audible_audio(self, path):
        self.calls.append(("has_audible_audio", path.name))
        return True

    def duration(self, path):
        if path.suffix == ".mp3":
            return 4.0
        return 20.0

    def build_clip(self, movie, segment, clip_path, resolution):
        self.calls.append(("build_clip", movie, segment.index, resolution))
        clip_path.write_text("clip", encoding="utf-8")

    def concat_clips(self, clips, output):
        self.calls.append(("concat_clips", len(list(clips))))
        output.write_text("silent", encoding="utf-8")

    def add_voice(self, video, voice, output):
        self.calls.append(("add_voice", video.name, voice.name, output.name))
        output.write_text("final", encoding="utf-8")


class NoAudioFakeEngine(FakeEngine):
    def has_audio_stream(self, path):
        self.calls.append(("has_audio_stream", path.name))
        return False


class SilentAudioFakeEngine(FakeEngine):
    def has_audible_audio(self, path):
        self.calls.append(("has_audible_audio", path.name))
        return False


class VideoProcessorTests(unittest.TestCase):
    def test_render_orchestrates_engine_calls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script = root / "script.txt"
            voice = root / "voice.mp3"
            movie = root / "movie.mp4"
            output = root / "out" / "review.mp4"
            script.write_text("Đoạn 1\n\nĐoạn 2", encoding="utf-8")
            voice.write_text("voice", encoding="utf-8")
            movie.write_text("movie", encoding="utf-8")
            logs = []
            engine = FakeEngine()

            VideoProcessor(engine=engine, logger=logs.append).render(
                RenderConfig(
                    script=script,
                    voice=voice,
                    movie=movie,
                    output=output,
                    resolution="720:1280",
                )
            )

            self.assertTrue(output.exists())
            self.assertIn(("require_tools",), engine.calls)
            self.assertIn(("has_audio_stream", "voice.mp3"), engine.calls)
            self.assertIn(("has_audible_audio", "voice.mp3"), engine.calls)
            self.assertEqual(
                [call[0] for call in engine.calls].count("build_clip"),
                2,
            )
            self.assertIn(("concat_clips", 2), engine.calls)
            self.assertTrue(any("Hoàn tất" in message for message in logs))

    def test_render_rejects_voice_without_audio_stream(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script = root / "script.txt"
            voice = root / "voice.mp3"
            movie = root / "movie.mp4"
            output = root / "out" / "review.mp4"
            script.write_text("Đoạn 1", encoding="utf-8")
            voice.write_text("not audio", encoding="utf-8")
            movie.write_text("movie", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "không có audio stream"):
                VideoProcessor(engine=NoAudioFakeEngine()).render(
                    RenderConfig(
                        script=script,
                        voice=voice,
                        movie=movie,
                        output=output,
                    )
                )

    def test_render_rejects_silent_voice(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script = root / "script.txt"
            voice = root / "voice.mp3"
            movie = root / "movie.mp4"
            output = root / "out" / "review.mp4"
            script.write_text("Đoạn 1", encoding="utf-8")
            voice.write_text("silent audio", encoding="utf-8")
            movie.write_text("movie", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "không có tiếng"):
                VideoProcessor(engine=SilentAudioFakeEngine()).render(
                    RenderConfig(
                        script=script,
                        voice=voice,
                        movie=movie,
                        output=output,
                    )
                )


if __name__ == "__main__":
    unittest.main()

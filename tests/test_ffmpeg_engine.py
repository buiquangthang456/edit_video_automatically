import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from engines.ffmpeg_engine import FFmpegEngine


class FFmpegEngineSubtitleTests(unittest.TestCase):
    def test_ass_subtitle_keeps_full_caption_and_uses_safe_margins(self):
        text = (
            "Trái lại, số 6 vẫn khen ngợi sự lì lợm của Knuckleduster, "
            "cho dù câu này dài hơn chiều rộng của một khung hình ngang thông thường."
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            subtitle = Path(temp_dir) / "caption.ass"

            FFmpegEngine()._write_subtitle_file(subtitle, text, 1280, 720)

            content = subtitle.read_text(encoding="utf-8-sig")
            self.assertIn("PlayResX: 1280", content)
            self.assertIn("PlayResY: 720", content)
            self.assertIn("WrapStyle: 0", content)
            self.assertIn(",77,77,58,1", content)
            self.assertIn(text, content)
            self.assertNotIn("...", content)

    def test_parse_resolution_rejects_invalid_dimensions(self):
        self.assertEqual(FFmpegEngine._parse_resolution("1280:720"), (1280, 720))
        for resolution in ("1280x720", "0:720", "abc:720", "1280:720:30"):
            with self.subTest(resolution=resolution):
                with self.assertRaises(ValueError):
                    FFmpegEngine._parse_resolution(resolution)


class FFmpegEngineAudioTests(unittest.TestCase):
    @patch("engines.ffmpeg_engine.shutil.which", return_value="ffmpeg")
    @patch("engines.ffmpeg_engine.subprocess.run")
    def test_has_audible_audio_uses_detected_peak(self, run_mock, _which_mock):
        run_mock.return_value = Mock(
            returncode=0,
            stderr="[Parsed_volumedetect] max_volume: -12.4 dB",
        )

        self.assertTrue(FFmpegEngine().has_audible_audio(Path("voice.mp3")))

        run_mock.return_value.stderr = "[Parsed_volumedetect] max_volume: -inf dB"
        self.assertFalse(FFmpegEngine().has_audible_audio(Path("silent.mp3")))

    def test_add_voice_encodes_compatible_default_stereo_audio(self):
        engine = FFmpegEngine()
        with (
            patch.object(engine, "_run") as run_mock,
            patch.object(engine, "has_audio_stream", return_value=True),
            patch.object(engine, "has_audible_audio", return_value=True),
        ):
            engine.add_voice(Path("video.mp4"), Path("voice.mp3"), Path("output.mp4"))

        command = run_mock.call_args.args[0]
        audio_filter = command[command.index("-filter:a") + 1]
        self.assertIn("loudnorm=I=-16:TP=-1.5:LRA=11", audio_filter)
        self.assertTrue(audio_filter.endswith("apad"))
        self.assertEqual(command[command.index("-map_metadata") + 1], "-1")
        self.assertEqual(command[command.index("-map_chapters") + 1], "-1")
        self.assertEqual(command[command.index("-ar") + 1], "48000")
        self.assertEqual(command[command.index("-ac") + 1], "2")
        self.assertEqual(command[command.index("-disposition:a:0") + 1], "default")


if __name__ == "__main__":
    unittest.main()

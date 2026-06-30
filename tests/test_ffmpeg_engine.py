import unittest
from pathlib import Path
from unittest.mock import patch

from engines.ffmpeg_engine import FFmpegEngine


class FFmpegEngineTests(unittest.TestCase):
    def test_caption_layout_fits_horizontal_and_vertical_outputs(self):
        vertical = FFmpegEngine._caption_layout("1080:1920")
        horizontal = FFmpegEngine._caption_layout("1920:1080")

        self.assertGreater(vertical[0], 20)
        self.assertGreater(horizontal[0], vertical[0])
        self.assertGreater(vertical[3], horizontal[3])

    @patch.object(FFmpegEngine, "has_audio_stream", return_value=True)
    @patch.object(FFmpegEngine, "_run")
    def test_add_voice_replaces_video_audio_with_selected_voice(self, run_mock, audio_mock):
        engine = FFmpegEngine()

        engine.add_voice(Path("silent.mp4"), Path("voice.mp3"), Path("out.mp4"))

        command = run_mock.call_args.args[0]
        self.assertIn("-map", command)
        self.assertIn("0:v:0", command)
        self.assertIn("1:a:0", command)
        self.assertIn("-af", command)
        self.assertIn("asetpts=PTS-STARTPTS,aresample=async=1:first_pts=0,volume=1.25,apad", command)
        self.assertIn("copy", command)
        self.assertIn("-disposition:a:0", command)
        self.assertIn("default", command)
        audio_mock.assert_called_once_with(Path("out.mp4"))


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path
from unittest.mock import patch

from engines.ffmpeg_engine import FFmpegEngine


class FFmpegEngineTests(unittest.TestCase):
    @patch.object(FFmpegEngine, "has_audio_stream", return_value=True)
    @patch.object(FFmpegEngine, "_run")
    def test_add_voice_replaces_video_audio_with_selected_voice(self, run_mock, audio_mock):
        engine = FFmpegEngine()

        engine.add_voice(Path("silent.mp4"), Path("voice.mp3"), Path("out.mp4"))

        command = run_mock.call_args.args[0]
        self.assertIn("-filter_complex", command)
        self.assertIn("[1:a:0]asetpts=PTS-STARTPTS,aresample=async=1:first_pts=0,volume=1.25,apad[voice_audio]", command)
        self.assertIn("-map", command)
        self.assertIn("0:v:0", command)
        self.assertIn("[voice_audio]", command)
        self.assertNotIn("1:a:0", command)
        self.assertIn("libx264", command)
        audio_mock.assert_called_once_with(Path("out.mp4"))


if __name__ == "__main__":
    unittest.main()
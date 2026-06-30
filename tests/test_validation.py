import tempfile
import unittest
from pathlib import Path

from utils.validation import validate_inputs


class ValidationTests(unittest.TestCase):
    def test_validate_inputs_accepts_supported_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script = root / "script.txt"
            voice = root / "voice.mp3"
            movie = root / "movie.mp4"
            for path in (script, voice, movie):
                path.write_text("x", encoding="utf-8")

            validate_inputs(script, voice, movie)

    def test_validate_inputs_rejects_unsupported_voice(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script = root / "script.txt"
            voice = root / "voice.txt"
            movie = root / "movie.mp4"
            for path in (script, voice, movie):
                path.write_text("x", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Voice"):
                validate_inputs(script, voice, movie)


if __name__ == "__main__":
    unittest.main()
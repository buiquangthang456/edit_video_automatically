import tempfile
import unittest
from pathlib import Path

from utils.text import escape_drawtext, read_script, shorten_caption


class TextUtilsTests(unittest.TestCase):
    def test_read_script_splits_blank_lines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "script.txt"
            script.write_text("Đoạn 1\n\nĐoạn 2", encoding="utf-8")

            self.assertEqual(read_script(script), ["Đoạn 1", "Đoạn 2"])

    def test_read_script_rejects_empty_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "script.txt"
            script.write_text("   ", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "trống"):
                read_script(script)

    def test_escape_drawtext_and_shorten_caption(self):
        escaped = escape_drawtext("A:B's 100%\\ok\nnext")

        self.assertIn("\\:", escaped)
        self.assertIn("\\'", escaped)
        self.assertIn("\\%", escaped)
        self.assertIn("\\\\", escaped)
        self.assertNotIn("\n", escaped)
        self.assertTrue(shorten_caption("word " * 100, width=20).endswith("..."))


if __name__ == "__main__":
    unittest.main()
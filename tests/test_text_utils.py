import tempfile
import unittest
from pathlib import Path

from utils.text import MAX_CAPTION_CHARS, escape_ass, escape_drawtext, read_script, shorten_caption


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

    def test_read_script_splits_all_long_paragraphs_without_losing_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "script.txt"
            paragraphs = ["một hai ba bốn năm " * 18, "sáu bảy tám chín mười " * 15]
            script.write_text("\n\n".join(paragraphs), encoding="utf-8")

            blocks = read_script(script)

            self.assertGreater(len(blocks), 2)
            self.assertTrue(all(len(block) <= MAX_CAPTION_CHARS for block in blocks))
            expected = " ".join(" ".join(paragraph.split()) for paragraph in paragraphs)
            self.assertEqual(" ".join(blocks), expected)

    def test_escape_drawtext_and_shorten_caption(self):
        escaped = escape_drawtext("A:B's 100%\\ok\nnext")

        self.assertIn("\\:", escaped)
        self.assertIn("\\'", escaped)
        self.assertIn("\\%", escaped)
        self.assertIn("\\\\", escaped)
        self.assertNotIn("\n", escaped)
        self.assertTrue(shorten_caption("word " * 100, width=20).endswith("..."))

    def test_escape_ass_preserves_text_and_escapes_control_sequences(self):
        escaped = escape_ass("Dòng {một}\\hai\nDòng ba")

        self.assertEqual(escaped, r"Dòng \{một\}\\hai\NDòng ba")


if __name__ == "__main__":
    unittest.main()

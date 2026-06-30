import unittest

from utils.text import wrap_caption


class TextTests(unittest.TestCase):
    def test_wrap_caption_keeps_every_word_and_adds_lines(self):
        text = "Đây là một câu phụ đề khá dài cần được hiển thị đầy đủ trong khung hình"

        wrapped = wrap_caption(text, width=24)

        self.assertIn("\n", wrapped)
        self.assertEqual(wrapped.replace("\n", " "), text)
        self.assertTrue(all(len(line) <= 24 for line in wrapped.splitlines()))

    def test_wrap_caption_normalizes_existing_whitespace(self):
        wrapped = wrap_caption("Một câu\n có   nhiều khoảng trắng", width=40)

        self.assertEqual(wrapped, "Một câu có nhiều khoảng trắng")


if __name__ == "__main__":
    unittest.main()

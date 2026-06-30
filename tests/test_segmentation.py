import unittest

from core.segmentation import make_segments


class SegmentationTests(unittest.TestCase):
    def test_make_segments_preserves_voice_duration_and_order(self):
        segments = make_segments(["short", "a much longer block of text"], 12.0, 120.0)

        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].index, 1)
        self.assertEqual(segments[1].index, 2)
        self.assertEqual(segments[0].start, 0.0)
        self.assertEqual(segments[-1].end, 12.0)
        self.assertGreater(segments[0].duration, 0)
        self.assertGreaterEqual(segments[1].source_start, segments[0].source_start)

    def test_make_segments_clamps_source_start_for_short_movie(self):
        segments = make_segments(["one", "two", "three"], 30.0, 10.0)

        self.assertEqual(len(segments), 3)
        self.assertTrue(all(segment.source_start >= 0 for segment in segments))
        self.assertEqual(segments[-1].end, 30.0)


if __name__ == "__main__":
    unittest.main()
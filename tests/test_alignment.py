import unittest

from core.alignment import align_segments_to_subtitles
from models.segment import Segment
from models.subtitle import SubtitleCue


class SourceAlignmentTests(unittest.TestCase):
    def test_alignment_preserves_order_and_can_jump_to_post_credit_scene(self):
        segments = [
            Segment(1, "Koichi gặp Captain Celebrity", 0.0, 4.0, 0.0),
            Segment(2, "Koichi kết thúc mùa cuối cùng của The Crawler", 4.0, 8.0, 40.0),
            Segment(3, "Trong phòng thí nghiệm, bác sĩ kiểm tra mẫu vật", 8.0, 12.0, 80.0),
        ]
        cues = [
            SubtitleCue(10.0, 12.0, "Koichi Captain Celebrity"),
            SubtitleCue(80.0, 82.0, "Koichi The Crawler final season"),
            SubtitleCue(180.0, 184.0, "Doctor status of the subject laboratory"),
        ]

        aligned = align_segments_to_subtitles(
            segments,
            cues,
            movie_duration=200.0,
        )

        self.assertLess(aligned[0].source_start, aligned[1].source_start)
        self.assertLess(aligned[1].source_start, aligned[2].source_start)
        self.assertGreater(aligned[2].source_start, 150.0)


if __name__ == "__main__":
    unittest.main()

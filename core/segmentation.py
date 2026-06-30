"""Script-to-timeline segmentation logic."""
from __future__ import annotations

from models.segment import Segment


def make_segments(
    script_blocks: list[str],
    voice_duration: float,
    movie_duration: float,
) -> list[Segment]:
    """Create timeline segments weighted by script block length."""
    total_chars = sum(max(1, len(block)) for block in script_blocks)
    cursor = 0.0
    usable_movie_duration = max(1.0, movie_duration - 8.0)
    step = usable_movie_duration / max(1, len(script_blocks))
    segments: list[Segment] = []

    for index, block in enumerate(script_blocks, start=1):
        share = max(1, len(block)) / total_chars
        duration = max(2.0, voice_duration * share)
        end = voice_duration if index == len(script_blocks) else min(voice_duration, cursor + duration)
        source_start = min(
            max(0.0, (index - 1) * step),
            max(0.0, movie_duration - (end - cursor) - 1.0),
        )
        segments.append(
            Segment(
                index=index,
                text=block,
                start=cursor,
                end=end,
                source_start=source_start,
            )
        )
        cursor = end

    if segments and segments[-1].end < voice_duration:
        last = segments[-1]
        segments[-1] = Segment(
            last.index,
            last.text,
            last.start,
            voice_duration,
            last.source_start,
        )
    return segments
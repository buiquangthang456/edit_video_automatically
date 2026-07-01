"""Script-to-timeline segmentation logic."""
from __future__ import annotations

from models.segment import Segment


def make_segments(
    script_blocks: list[str],
    voice_duration: float,
    movie_duration: float,
    voice_boundaries: list[float] | None = None,
) -> list[Segment]:
    """Create a voice timeline and approximate source positions.

    Character weights provide the baseline timing. Caption boundaries are then
    snapped to nearby silence points when available, which keeps subtitle
    changes from happening in the middle of spoken phrases.
    """
    if not script_blocks:
        return []
    if voice_duration <= 0:
        raise ValueError("Thời lượng voice-over phải lớn hơn 0.")

    weights = [max(1, sum(character.isalnum() for character in block)) for block in script_blocks]
    total_weight = sum(weights)
    raw_boundaries = [0.0]
    cumulative = 0
    for weight in weights[:-1]:
        cumulative += weight
        raw_boundaries.append(voice_duration * cumulative / total_weight)
    raw_boundaries.append(voice_duration)

    boundaries = _snap_to_voice_pauses(raw_boundaries, voice_boundaries or [], voice_duration)
    usable_movie_duration = max(0.0, movie_duration - 0.05)
    segments: list[Segment] = []

    for index, block in enumerate(script_blocks, start=1):
        start = boundaries[index - 1]
        end = boundaries[index]
        progress = start / voice_duration
        duration = end - start
        source_start = min(progress * usable_movie_duration, max(0.0, movie_duration - duration - 0.05))
        segments.append(
            Segment(
                index=index,
                text=block,
                start=start,
                end=end,
                source_start=source_start,
            )
        )
    return segments


def _snap_to_voice_pauses(
    raw_boundaries: list[float], pause_boundaries: list[float], voice_duration: float
) -> list[float]:
    if len(raw_boundaries) <= 2:
        return raw_boundaries

    segment_count = len(raw_boundaries) - 1
    minimum_duration = min(0.8, voice_duration / segment_count * 0.35)
    pauses = sorted(pause for pause in pause_boundaries if 0.0 < pause < voice_duration)
    snapped = [0.0]

    for index, target in enumerate(raw_boundaries[1:-1], start=1):
        lower = snapped[-1] + minimum_duration
        remaining = segment_count - index
        upper = voice_duration - remaining * minimum_duration
        nearby = [pause for pause in pauses if lower <= pause <= upper and abs(pause - target) <= 1.5]
        boundary = min(nearby, key=lambda pause: abs(pause - target)) if nearby else target
        snapped.append(min(upper, max(lower, boundary)))

    snapped.append(voice_duration)
    return snapped

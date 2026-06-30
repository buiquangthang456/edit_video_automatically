"""Timeline data structures."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    """A script/video segment to render from the source movie."""

    index: int
    text: str
    start: float
    end: float
    source_start: float

    @property
    def duration(self) -> float:
        """Return the segment duration, clamped to a small positive value."""
        return max(0.1, self.end - self.start)
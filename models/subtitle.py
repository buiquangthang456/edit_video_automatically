"""Subtitle data structures used to align a script with source footage."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubtitleCue:
    """One text subtitle cue from the source video."""

    start: float
    end: float
    text: str

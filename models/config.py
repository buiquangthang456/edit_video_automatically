"""Configuration models for Movie Auto Editor."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RenderConfig:
    """User-provided render settings."""

    script: Path
    voice: Path
    movie: Path
    output: Path
    resolution: str = "1080:1920"
"""Backward-compatible executable wrapper for Movie Auto Editor.

Main application code lives in app/, core/, engines/, models/, and utils/.
"""
from __future__ import annotations

from app.cli import main


if __name__ == "__main__":
    main()
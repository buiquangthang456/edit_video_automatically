"""Text parsing and escaping helpers."""
from __future__ import annotations

import re
import textwrap
from pathlib import Path


MAX_CAPTION_CHARS = 96


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?…])\s+")


def read_script(path: Path) -> list[str]:
    """Read a UTF-8 text script and return all renderable captions."""
    return [caption for section in read_script_sections(path) for caption in section]


def read_script_sections(path: Path) -> list[list[str]]:
    """Read a script while preserving paragraphs for source-scene alignment.

    Blank lines describe logical sections of the story.  Within each section,
    sentence boundaries are kept whenever possible so subtitle changes can be
    snapped to natural pauses in the voice-over.
    """
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        raise ValueError("File kịch bản đang trống.")

    sections: list[list[str]] = []
    paragraphs = [block for block in re.split(r"\n\s*\n", text) if block.strip()]
    for paragraph in paragraphs:
        normalized = " ".join(paragraph.split())
        captions: list[str] = []
        for sentence in _SENTENCE_BOUNDARY.split(normalized):
            captions.extend(
                textwrap.wrap(
                    sentence,
                    width=MAX_CAPTION_CHARS,
                    break_long_words=True,
                    break_on_hyphens=False,
                )
            )
        if captions:
            sections.append(captions)
    return sections


def escape_drawtext(text: str) -> str:
    """Escape text for FFmpeg drawtext filter values."""
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace("\n", " ")
    )


def wrap_caption(text: str, width: int) -> str:
    """Wrap a caption into multiple lines without splitting normal words."""
    normalized = " ".join(text.split())
    return "\n".join(
        textwrap.wrap(
            normalized,
            width=max(1, width),
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def shorten_caption(text: str, width: int = 130) -> str:
    """Shorten a subtitle caption without splitting words aggressively."""
    return textwrap.shorten(text, width=width, placeholder="...")


def escape_ass(text: str) -> str:
    """Escape user text for the ASS dialogue text field without truncating it."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return (
        normalized.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )

"""Text parsing and escaping helpers."""
from __future__ import annotations

import textwrap
from pathlib import Path


MAX_CAPTION_CHARS = 110


def read_script(path: Path) -> list[str]:
    """Read a UTF-8 text script and split it into renderable blocks."""
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        raise ValueError("File kịch bản đang trống.")

    blocks: list[str] = []
    paragraphs = [block for block in text.split("\n\n") if block.strip()]
    for paragraph in paragraphs:
        normalized = " ".join(paragraph.split())
        blocks.extend(
            textwrap.wrap(
                normalized,
                width=MAX_CAPTION_CHARS,
                break_long_words=True,
                break_on_hyphens=False,
            )
        )
    return blocks


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

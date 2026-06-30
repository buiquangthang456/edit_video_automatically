"""Command-line interface for Movie Auto Editor."""
from __future__ import annotations

import argparse
from pathlib import Path

from core.video_processor import VideoProcessor
from models.config import RenderConfig


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Tự dựng video review từ kịch bản, voice-over và video phim."
    )
    parser.add_argument("--script", required=True, type=Path, help="File .txt chứa kịch bản review")
    parser.add_argument("--voice", required=True, type=Path, help="File voice-over đã tạo sẵn")
    parser.add_argument("--movie", required=True, type=Path, help="File video phim nguồn")
    parser.add_argument(
        "--output",
        default=Path("outputs/review_video.mp4"),
        type=Path,
        help="File video xuất ra",
    )
    parser.add_argument(
        "--resolution",
        default="1080:1920",
        help="Kích thước xuất, ví dụ 1080:1920 hoặc 1920:1080",
    )
    return parser.parse_args()


def main() -> None:
    """Run the CLI entry point."""
    args = parse_args()
    config = RenderConfig(
        script=args.script,
        voice=args.voice,
        movie=args.movie,
        output=args.output,
        resolution=args.resolution,
    )
    VideoProcessor().render(config)


if __name__ == "__main__":
    main()
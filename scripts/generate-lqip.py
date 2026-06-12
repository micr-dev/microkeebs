#!/usr/bin/env python3
"""Generate LQIP (Low Quality Image Placeholders) — tiny pixelated PNGs."""

import argparse
import os
import sys
from pathlib import Path

from PIL import Image

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public" / "images"
LQIP_DIR = PUBLIC_DIR / "lqip"
TARGET_WIDTH = 20
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".webp"}


def get_lqip_path(src: Path) -> Path:
    """Derive the LQIP output path from a source image path.

    public/images/<videoId>/thumbnail.jpg -> public/images/lqip/<videoId>/thumbnail-lqip.png
    """
    rel = src.relative_to(PUBLIC_DIR)
    video_id = rel.parts[0]
    stem = rel.stem
    return LQIP_DIR / video_id / f"{stem}-lqip.png"


def generate_lqip(src: Path, dst: Path, *, force: bool = False) -> bool:
    """Generate a single LQIP. Returns True if generated, False if skipped."""
    if dst.exists() and not force:
        if dst.stat().st_mtime >= src.stat().st_mtime:
            return False  # up-to-date

    dst.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(src) as img:
        # Resize to TARGET_WIDTH with nearest-neighbour for that pixelated look
        ratio = TARGET_WIDTH / img.width
        new_h = max(1, round(img.height * ratio))
        small = img.resize((TARGET_WIDTH, new_h), Image.NEAREST)
        small.save(dst, "PNG")

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate LQIP pixel placeholders")
    parser.add_argument("--force", action="store_true", help="Regenerate all LQIPs")
    args = parser.parse_args()

    if not PUBLIC_DIR.exists():
        print(f"Error: images directory not found at {PUBLIC_DIR}", file=sys.stderr)
        sys.exit(1)

    image_dirs = sorted(
        d for d in PUBLIC_DIR.iterdir() if d.is_dir() and d.name != "lqip"
    )

    generated = 0
    skipped = 0
    errors = 0

    for video_dir in image_dirs:
        for img_file in sorted(video_dir.iterdir()):
            if img_file.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            # Skip already-optimized small thumbnails
            if "_sm" in img_file.stem:
                continue

            dst = get_lqip_path(img_file)
            try:
                if generate_lqip(img_file, dst, force=args.force):
                    print(f"  ✅ {dst.relative_to(LQIP_DIR.parent)}")
                    generated += 1
                else:
                    skipped += 1
            except Exception as exc:
                print(f"  ❌ {img_file.name}: {exc}", file=sys.stderr)
                errors += 1

    print(
        f"\n--- LQIP Generation Summary ---\n"
        f"  Generated : {generated}\n"
        f"  Skipped   : {skipped}\n"
        f"  Errors    : {errors}"
    )


if __name__ == "__main__":
    main()

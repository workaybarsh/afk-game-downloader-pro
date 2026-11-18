"""Build the application icon (app.ico + preview png) from a source image.

Usage:
    python tools/make_icon.py [source-image]
Default source: assets/icon_source.png
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def to_square(image: Image.Image) -> Image.Image:
    width, height = image.size
    if width == height:
        return image
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side))


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    assets = root / "assets"
    assets.mkdir(exist_ok=True)

    source = Path(sys.argv[1]) if len(sys.argv) > 1 else assets / "icon_source.png"
    if not source.is_file():
        print(f"source image not found: {source}")
        return 1

    image = to_square(Image.open(source).convert("RGBA"))
    base = image.resize((256, 256), Image.LANCZOS)

    base.save(assets / "app.ico", format="ICO", sizes=SIZES)
    base.save(assets / "app_preview.png", format="PNG")
    for size in (16, 32, 48, 64, 128):
        base.resize((size, size), Image.LANCZOS).save(assets / f"icon_{size}.png", format="PNG")

    print(f"icon built from {source.name} -> {assets / 'app.ico'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

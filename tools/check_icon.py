"""Verify that an executable carries the application icon.

Extracts the embedded icon with .NET and compares it to assets/app.ico.
A mean pixel difference below the threshold means "same artwork".

Usage:
    python tools/check_icon.py "dist/AFK Game Downloader Pro.exe"
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

HERE = Path(__file__).resolve().parent.parent
REFERENCE = HERE / "assets" / "app.ico"
SIZE = 32
THRESHOLD = 22.0


def extract_icon(exe: Path, output: Path) -> bool:
    script = (
        "Add-Type -AssemblyName System.Drawing; "
        f"$i = [System.Drawing.Icon]::ExtractAssociatedIcon('{exe}'); "
        f"$i.ToBitmap().Save('{output}', [System.Drawing.Imaging.ImageFormat]::Png)"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        creationflags=0x08000000,
        timeout=60,
    )
    return output.is_file() and output.stat().st_size > 0


def difference(a: Image.Image, b: Image.Image) -> float:
    ia = a.convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)
    ib = b.convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)
    stats = ImageStat.Stat(ImageChops.difference(ia, ib))
    return sum(stats.mean) / len(stats.mean)


def check(exe: Path) -> tuple[bool, float]:
    if not exe.is_file():
        return False, 999.0
    reference = Image.open(REFERENCE).convert("RGBA")
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "icon.png"
        if not extract_icon(exe, png):
            return False, 999.0
        extracted = Image.open(png).convert("RGBA")
        score = difference(reference, extracted)
        return score <= THRESHOLD, score


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    ok = True
    for raw in argv[1:]:
        exe = Path(raw)
        matched, score = check(exe)
        print(f"{'OK  ' if matched else 'FAIL'}  {exe.name}  (difference {score:.1f})")
        ok = ok and matched
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

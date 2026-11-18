"""Build English promo images for the repository from a real UI screenshot.

Output: docs/promo-hero.png, docs/promo-safety.png, docs/promo-features.png
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SHOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "AppData/Local/Temp/afk_promo_shot.png"

BG = (13, 17, 23)
CARD = (22, 27, 34)
CARD2 = (33, 38, 45)
BORDER = (48, 54, 61)
FG = (230, 237, 243)
MUTED = (139, 148, 158)
ACCENT = (47, 129, 247)
GREEN = (63, 185, 80)
AMBER = (210, 153, 34)

W, H = 1200, 630
FONT_DIR = Path(r"C:\Windows\Fonts")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


BOLD = "segoeuib.ttf"
SEMI = "seguisb.ttf"
REG = "segoeui.ttf"
MONO = "consola.ttf"


def rounded(image: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, image.size[0], image.size[1]), radius, fill=255)
    result = Image.new("RGBA", image.size, (0, 0, 0, 0))
    result.paste(image, (0, 0), mask)
    return result


def frame(image: Image.Image, border: tuple[int, int, int], width: int = 2) -> Image.Image:
    canvas = Image.new("RGBA", (image.size[0] + width * 2, image.size[1] + width * 2), border)
    mask = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, canvas.size[0], canvas.size[1]), 14, fill=255)
    out = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    out.paste(canvas, (0, 0), mask)
    out.paste(image, (width, width), image)
    return out


def paste_shot(base: Image.Image, shot_path: Path, box: tuple[int, int, int, int]) -> None:
    if not shot_path.is_file():
        return
    shot = Image.open(shot_path).convert("RGB")
    # drop the window border/shadow captured around the client area
    inset = 6
    shot = shot.crop((inset, 0, shot.width - inset, shot.height - 16))
    max_w = box[2] - box[0]
    max_h = box[3] - box[1]
    scale = min(max_w / shot.width, max_h / shot.height)
    shot = shot.resize((int(shot.width * scale), int(shot.height * scale)), Image.LANCZOS)
    card = frame(rounded(shot, 12), BORDER)
    x = box[0] + (max_w - card.width) // 2
    y = box[1] + (max_h - card.height) // 2
    base.alpha_composite(card, (x, y))


def hero() -> None:
    image = Image.new("RGBA", (W, H), BG)
    draw = ImageDraw.Draw(image)

    icon = Image.open(ROOT / "assets" / "icon_128.png").convert("RGBA").resize((88, 88), Image.LANCZOS)
    image.alpha_composite(icon, (60, 52))

    draw.text((60, 164), "AFK Game", font=font(BOLD, 44), fill=FG)
    draw.text((60, 216), "Downloader Pro", font=font(BOLD, 44), fill=ACCENT)

    draw.text((62, 288), "Downloads finish.", font=font(REG, 21), fill=FG)
    draw.text((62, 316), "The PC powers off.", font=font(REG, 21), fill=FG)
    draw.text((62, 344), "You sleep.", font=font(REG, 21), fill=FG)

    chips = [("Steam", ACCENT), ("Epic Games", ACCENT), ("Verified, not guessed", GREEN)]
    y = 400
    for label, color in chips:
        width = draw.textlength(label, font=font(SEMI, 15)) + 26
        draw.rounded_rectangle((62, y, 62 + width, y + 34), 17, fill=CARD2, outline=BORDER)
        draw.text((75, y + 8), label, font=font(SEMI, 15), fill=color)
        y += 44

    draw.text((62, 566), "github.com/workaybarsh", font=font(MONO, 13), fill=MUTED)
    draw.text((62, 586), "/afk-game-downloader-pro", font=font(MONO, 13), fill=MUTED)

    paste_shot(image, SHOT, (556, 60, 1140, 570))
    image.convert("RGB").save(DOCS / "promo-hero.png")


def safety() -> None:
    image = Image.new("RGBA", (W, H), BG)
    draw = ImageDraw.Draw(image)

    draw.text((64, 56), "It never guesses.", font=font(BOLD, 44), fill=FG)
    draw.text(
        (64, 116),
        "A shutdown happens only when every one of these is true.",
        font=font(REG, 20),
        fill=MUTED,
    )

    items = [
        "A watched download was actually observed",
        "Every watched app is fully installed",
        "Byte counters match the manifest",
        "Steam's own log says Fully Installed",
        "The transfer rate is idle",
        "The state stays calm for 120 seconds",
        "Every manifest is re-read the moment the countdown ends",
    ]

    y = 176
    for index, text in enumerate(items, start=1):
        draw.rounded_rectangle((64, y, 600, y + 46), 10, fill=CARD, outline=BORDER)
        draw.ellipse((80, y + 13, 100, y + 33), fill=(15, 61, 31), outline=GREEN)
        draw.text((84, y + 14), "✓", font=font(SEMI, 14), fill=GREEN)
        draw.text((116, y + 13), text, font=font(REG, 17), fill=FG)
        y += 56

    card = Image.new("RGBA", (500, 300), CARD)
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle((0, 0, 499, 299), 14, outline=BORDER, width=2)
    cd.text((24, 22), "Proof, written to the log", font=font(SEMI, 16), fill=MUTED)
    lines = [
        ("COMPLETED: Red Dead Redemption 2", GREEN),
        ("Proof: flags=4, 112.6 GB/112.6 GB", FG),
        ("       log='Fully Installed'", FG),
        ("Action in 60s: Shut down computer", AMBER),
    ]
    ty = 64
    for text, color in lines:
        cd.text((24, ty), text, font=font(MONO, 14), fill=color)
        ty += 34
    cd.text((24, 220), "Stop or Cancel is available the whole time.", font=font(REG, 15), fill=MUTED)

    image.alpha_composite(card, (636, 176))
    image.convert("RGB").save(DOCS / "promo-safety.png")


def features() -> None:
    image = Image.new("RGBA", (W, H), BG)
    draw = ImageDraw.Draw(image)

    draw.text((64, 56), "Built for leaving the PC alone", font=font(BOLD, 40), fill=FG)
    draw.text((64, 110), "What you get on top of a plain shutdown timer.", font=font(REG, 19), fill=MUTED)

    cards = [
        ("Game list", "Every download found, with speed, ETA\nand the space it takes on disk."),
        ("Pick what matters", "Tick the games that must finish.\nRefresh pulls in new downloads."),
        ("Always accurate", "Reads the manifests every 2 seconds,\nre-scans libraries every 60 seconds."),
        ("Dry run", "Test mode runs the whole verification\nbut never touches the PC."),
        ("Two languages", "English and Turkish, one click,\nremembered between launches."),
        ("Clean install", "Setup and uninstall wizards, custom icon,\nMIT licensed, no background leftovers."),
    ]

    for index, (title, body) in enumerate(cards):
        col = index % 3
        row = index // 3
        x = 64 + col * 364
        y = 176 + row * 210
        card = Image.new("RGBA", (344, 190), CARD)
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle((0, 0, 343, 189), 14, outline=BORDER, width=2)
        cd.rounded_rectangle((22, 22, 46, 46), 7, fill=(18, 58, 99))
        cd.text((29, 25), str(index + 1), font=font(SEMI, 14), fill=(158, 203, 255))
        cd.text((22, 62), title, font=font(SEMI, 20), fill=FG)
        cd.multiline_text((22, 96), body, font=font(REG, 15), fill=MUTED, spacing=5)
        image.alpha_composite(card, (x, y))

    image.convert("RGB").save(DOCS / "promo-features.png")


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    if not SHOT.is_file():
        print(f"screenshot not found: {SHOT}")
        return 1
    hero()
    safety()
    features()
    for name in ("promo-hero.png", "promo-safety.png", "promo-features.png"):
        path = DOCS / name
        print(f"{path}  {path.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

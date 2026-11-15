#!/usr/bin/env python3
"""Generate the Tauri app icons (icons are binary, so they are not committed).

Usage: python3 desktop/tools/make_icons.py   (requires Pillow)
Writes desktop/src-tauri/icons/icon.png and icon.ico.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "src-tauri" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([16, 16, 496, 496], radius=96, fill=(47, 111, 237, 255))
try:
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 210)
except Exception:
    font = ImageFont.load_default()
d.text((256, 268), "PJ", font=font, fill=(255, 255, 255, 255), anchor="mm")
img.save(OUT / "icon.png")
img.save(OUT / "icon.ico", sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])
print("wrote", OUT / "icon.png", "and icon.ico")

#!/usr/bin/env python3
"""Build deterministic target-cover pages with the book title on the same page."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat


WIDTH = 1080
HEIGHT = 1440
SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FONT = SKILL_ROOT / "assets/fonts/杨任东竹石体-Heavy.ttf"


def contain(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    scale = min(max_width / image.width, max_height / image.height)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def draw_centered_text(
    image: Image.Image,
    text: str,
    font: ImageFont.FreeTypeFont,
    y: int,
    fill: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    draw = ImageDraw.Draw(image)
    box = draw.textbbox((0, 0), text, font=font, stroke_width=0)
    width = box[2] - box[0]
    if width > WIDTH - 80:
        raise ValueError(f"书名超出安全区：{text}")
    x = (WIDTH - width) // 2
    shadow = (255, 255, 255, 115) if sum(fill[:3]) < 400 else (0, 0, 0, 150)
    draw.text((x + 4, y + 5), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)
    return (x, y, x + width, y + box[3] - box[1])


def main() -> int:
    parser = argparse.ArgumentParser(description="生成书名与目标真实封面同页的片头定帧")
    parser.add_argument("--cover", required=True, type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT)
    args = parser.parse_args()

    if not args.version.startswith("v") or not args.version[1:].isdigit():
        raise ValueError("--version 必须为 vNNN")
    if not args.cover.is_file():
        raise FileNotFoundError(args.cover)
    if not args.font.is_file():
        raise FileNotFoundError(args.font)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    base_path = args.output_dir / f"target-cover-base-{args.version}.png"
    title_page_path = args.output_dir / f"target-cover-title-page-{args.version}.png"
    metadata_path = args.output_dir / f"target-cover-title-page-{args.version}.json"
    for path in (base_path, title_page_path, metadata_path):
        if path.exists():
            raise FileExistsError(f"版本素材已存在，不覆盖：{path}")

    cover = Image.open(args.cover).convert("RGB")
    background = ImageOps.fit(cover, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(radius=34)).convert("RGBA")
    veil = Image.new("RGBA", (WIDTH, HEIGHT), (245, 245, 241, 108))
    background = Image.alpha_composite(background, veil)

    cover_top = 250
    cover_bottom = 1320
    fitted = contain(cover, 840, cover_bottom - cover_top)
    cover_x = (WIDTH - fitted.width) // 2
    cover_y = cover_top + (cover_bottom - cover_top - fitted.height) // 2

    shadow = Image.new("RGBA", (fitted.width + 56, fitted.height + 56), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (18, 18, fitted.width + 38, fitted.height + 38),
        radius=10,
        fill=(0, 0, 0, 105),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=18))
    background.alpha_composite(shadow, (cover_x - 28, cover_y - 18))

    frame = Image.new("RGBA", (fitted.width + 20, fitted.height + 20), (255, 255, 255, 238))
    background.alpha_composite(frame, (cover_x - 10, cover_y - 10))
    background.alpha_composite(fitted.convert("RGBA"), (cover_x, cover_y))
    background.convert("RGB").save(base_path, quality=95)

    title_page = background.copy()
    font = ImageFont.truetype(str(args.font), 88)
    title_text = f"《{args.title}》"
    top_luminance = ImageStat.Stat(title_page.crop((0, 40, WIDTH, 225)).convert("L")).mean[0]
    title_color = (42, 39, 36, 255) if top_luminance > 145 else (255, 255, 255, 255)
    title_box = draw_centered_text(title_page, title_text, font, 70, title_color)
    title_page.convert("RGB").save(title_page_path, quality=95)

    metadata = {
        "version": args.version,
        "mode": "same_page_as_cover",
        "title": args.title,
        "source_cover": str(args.cover.resolve()),
        "base_asset": str(base_path.resolve()),
        "title_page_asset": str(title_page_path.resolve()),
        "canvas": {"width": WIDTH, "height": HEIGHT},
        "title_safe_area": {"top": 60, "bottom": 220},
        "cover_safe_area": {"top": cover_top, "bottom": cover_bottom},
        "title_box": {"left": title_box[0], "top": title_box[1], "right": title_box[2], "bottom": title_box[3]},
        "cover_box": {"left": cover_x, "top": cover_y, "right": cover_x + fitted.width, "bottom": cover_y + fitted.height},
        "cover_visible_during_title_motion": True,
        "waterwave_source": "title_page_asset",
        "author_baked_in": False,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

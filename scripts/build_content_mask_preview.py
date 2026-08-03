#!/usr/bin/env python3
"""Build the stage-one two-character mask confirmation card and record."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1080
HEIGHT = 1440
SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FONT = SKILL_ROOT / "assets/fonts/杨任东竹石体-Heavy.ttf"


def fit_font(text: str, path: Path, max_width: int, start_size: int) -> ImageFont.FreeTypeFont:
    size = start_size
    while size >= 32:
        font = ImageFont.truetype(str(path), size=size)
        box = font.getbbox(text)
        if box[2] - box[0] <= max_width:
            return font
        size -= 4
    raise ValueError(f"文字过长，无法排版: {text}")


def normalized_hook(value: str) -> list[str]:
    lines = [line.strip() for line in re.sub(r"\\+n", "\n", value).splitlines() if line.strip()]
    if not lines or len(lines) > 2:
        raise ValueError("情绪钩子必须是 1–2 行")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="生成第一阶段两字遮罩确认图")
    parser.add_argument("--keyword", required=True, help="固定为两个汉字")
    parser.add_argument("--hook", required=True, help="片头情绪句，最多两行，使用 \\n 分隔")
    parser.add_argument("--alpha-mask", required=True, type=Path, help="1080×1440 黑底白字毛笔候选")
    parser.add_argument("--output", required=True, type=Path, help="02-情绪提炼/mask-preview-vNNN.png")
    parser.add_argument("--record", required=True, type=Path, help="02-情绪提炼/mask-keyword-vNNN.json")
    parser.add_argument("--version", default="v001")
    args = parser.parse_args()

    keyword = args.keyword.strip()
    if not re.fullmatch(r"[\u3400-\u9fff]{2}", keyword):
        raise ValueError("遮罩关键词必须且只能是两个汉字")
    if not re.fullmatch(r"v\d{3}", args.version):
        raise ValueError("version 必须符合 vNNN")

    alpha_path = args.alpha_mask.expanduser().resolve()
    output = args.output.expanduser().resolve()
    record = args.record.expanduser().resolve()
    if not alpha_path.is_file():
        raise FileNotFoundError(f"遮罩候选不存在: {alpha_path}")
    if "02-情绪提炼" not in alpha_path.parts:
        raise ValueError("第一阶段遮罩候选必须位于 02-情绪提炼")
    if output.exists() or record.exists():
        raise FileExistsError("确认图或记录已存在，请升级版本")
    if "02-情绪提炼" not in output.parts or "02-情绪提炼" not in record.parts:
        raise ValueError("第一阶段遮罩确认图和记录必须位于 02-情绪提炼")

    mask = Image.open(alpha_path).convert("L")
    if mask.size != (WIDTH, HEIGHT):
        raise ValueError(f"遮罩候选必须是 {WIDTH}×{HEIGHT}，当前为 {mask.width}×{mask.height}")
    histogram = mask.histogram()
    if sum(histogram[17:]) < 1000:
        raise ValueError("遮罩候选几乎全黑，没有可确认的字形")

    lines = normalized_hook(args.hook)
    preview = Image.new("RGB", (WIDTH, HEIGHT), (4, 5, 7))
    draw = ImageDraw.Draw(preview)

    hook_font = fit_font(max(lines, key=len), DEFAULT_FONT, 860, 58)
    y = 230
    for line in lines:
        box = draw.textbbox((0, 0), line, font=hook_font)
        x = (WIDTH - (box[2] - box[0])) // 2
        draw.text((x, y), line, font=hook_font, fill=(246, 246, 242))
        y += 78

    gradient_strip = Image.new("RGB", (1, HEIGHT))
    pixels = gradient_strip.load()
    for row in range(HEIGHT):
        progress = row / max(1, HEIGHT - 1)
        color = (
            round(228 - 55 * progress),
            round(201 + 28 * progress),
            round(151 + 68 * progress),
        )
        pixels[0, row] = color
    gradient = gradient_strip.resize((WIDTH, HEIGHT))
    preview.paste(gradient, (0, 0), mask)

    footer_font = ImageFont.truetype(str(DEFAULT_FONT), size=34)
    footer = f"第一阶段遮罩确认｜{keyword}｜固定 2 字"
    footer_box = draw.textbbox((0, 0), footer, font=footer_font)
    footer_x = (WIDTH - (footer_box[2] - footer_box[0])) // 2
    draw.rounded_rectangle((footer_x - 28, 1265, footer_x + footer_box[2] - footer_box[0] + 28, 1330), radius=18, fill=(24, 27, 31))
    draw.text((footer_x, 1277), footer, font=footer_font, fill=(225, 225, 220))

    output.parent.mkdir(parents=True, exist_ok=True)
    preview.save(output)
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": args.version,
                "approval_stage": "content_package",
                "keyword": keyword,
                "han_count": 2,
                "hook": "\n".join(lines),
                "alpha_mask": str(alpha_path),
                "preview": str(output),
                "preview_type": "actual_alpha_mask_confirmation",
                "review_status": "awaiting_confirmation",
                "downstream_policy": "reuse_exact_approved_mask",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"preview": str(output), "record": str(record)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

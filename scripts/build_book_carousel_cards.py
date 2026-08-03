#!/usr/bin/env python3
"""从真实书封清单按动态轮播计划生成 1080×1440 全屏卡。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


WIDTH, HEIGHT = 1080, 1440


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_title(value: Any) -> str:
    return re.sub(r"[\s《》〈〉·,，。.!！?？:：;；'\"“”‘’_-]+", "", str(value or "")).casefold()


def safe_name(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u3400-\u9fff]+", "-", value).strip("-") or "book"


def render_card(source: Path, output: Path) -> None:
    with Image.open(source) as opened:
        cover = ImageOps.exif_transpose(opened).convert("RGB")
    background = ImageOps.fit(cover, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(34))
    background = ImageEnhance.Brightness(background).enhance(0.68)

    foreground = cover.copy()
    foreground.thumbnail((780, 1090), Image.Resampling.LANCZOS)
    bordered = ImageOps.expand(foreground, border=8, fill=(248, 246, 240))
    shadow = Image.new("RGBA", (bordered.width + 46, bordered.height + 46), (0, 0, 0, 0))
    shadow_box = Image.new("RGBA", bordered.size, (0, 0, 0, 165)).filter(ImageFilter.GaussianBlur(15))
    shadow.alpha_composite(shadow_box, (23, 25))
    shadow.alpha_composite(bordered.convert("RGBA"), (8, 8))
    x = (WIDTH - shadow.width) // 2
    y = (HEIGHT - shadow.height) // 2
    canvas = background.convert("RGBA")
    canvas.alpha_composite(shadow, (x, y))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, quality=95)


def main() -> int:
    parser = argparse.ArgumentParser(description="按动态轮播计划生成真实书封卡")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--project", type=Path, help="项目根目录；提供后卡片 asset 写成项目相对路径")
    parser.add_argument("--target-title", required=True)
    parser.add_argument("--version", default="v001")
    args = parser.parse_args()

    manifest_path = args.manifest.expanduser().resolve()
    plan_path = args.plan.expanduser().resolve()
    manifest = read_json(manifest_path)
    plan = read_json(plan_path)
    count = int(plan.get("card_count") or 0)
    frames = plan.get("card_frames", [])
    durations = plan.get("card_durations", [])
    if count <= 0 or len(frames) != count or len(durations) != count:
        raise SystemExit("轮播计划的 card_count、card_frames、card_durations 不一致")

    target = normalize_title(args.target_title)
    candidates: list[tuple[int, dict[str, Any], Path]] = []
    for index, item in enumerate(manifest.get("covers", []), start=1):
        if not isinstance(item, dict):
            continue
        title = item.get("titleZh") or item.get("title")
        source = manifest_path.parent / str(item.get("file") or "")
        if normalize_title(title) != target and source.is_file():
            candidates.append((int(item.get("order") or index), item, source))
    candidates.sort(key=lambda row: row[0])
    if len(candidates) < count:
        raise SystemExit(
            f"真实书封库只有 {len(candidates)} 张非目标封面，当前轮播计划需要 {count} 张"
        )

    output_dir = args.output_dir.expanduser().resolve()
    project = args.project.expanduser().resolve() if args.project else None
    if project is not None:
        try:
            output_dir.relative_to(project)
        except ValueError as exc:
            raise SystemExit("--output-dir 必须位于 --project 内") from exc
    output_dir.mkdir(parents=True, exist_ok=True)
    cards: list[dict[str, Any]] = []
    for card_index, (_, item, source) in enumerate(candidates[:count], start=1):
        title = str(item.get("titleZh") or item.get("title") or f"书籍{card_index}")
        output = output_dir / f"card-{card_index:02d}-{safe_name(title)}-{args.version}.png"
        render_card(source, output)
        cards.append({
            "index": card_index,
            "title": title,
            "author": item.get("author"),
            "source_cover": str(source),
            "source_page": item.get("sourcePage") or item.get("source_page"),
            "asset": str(output.relative_to(project)) if project is not None else str(output),
            "frames": int(frames[card_index - 1]),
            "duration": float(durations[card_index - 1]),
            "role": "carousel",
        })

    record = {
        "version": args.version,
        "template": "masked_book_carousel",
        "plan": str(plan_path),
        "timing_source_type": plan.get("timing_source_type"),
        "target_title": args.target_title,
        "target_in_carousel": False,
        "card_count": count,
        "card_frames": frames,
        "card_durations": durations,
        "carousel_start": plan.get("carousel_start"),
        "carousel_end": plan.get("carousel_end"),
        "carousel_motion": {
            "type": "snap_settle",
            "scale_start": 1.035,
            "scale_end": 1.0,
            "soft_focus_px": 1.5,
            "transition": "hard_cut",
        },
        "cards": cards,
    }
    record_path = output_dir / f"carousel-cards-{args.version}.json"
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(record_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

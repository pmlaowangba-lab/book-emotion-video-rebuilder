#!/usr/bin/env python3
"""按书名口播时码计算片头书封轮播数量与逐卡帧数。"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def han_count(text: str) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", text or ""))


def normalize_title(value: Any) -> str:
    return re.sub(r"[\s《》〈〉·,，。.!！?？:：;；'\"“”‘’_-]+", "", str(value or "")).casefold()


def actual_title_start(timing: dict[str, Any]) -> float | None:
    delivery = timing.get("book_title_delivery", {})
    for key in ("title_start_seconds", "title_start"):
        value = delivery.get(key)
        if value is not None:
            return float(value)
    return None


def estimated_title_start(
    script: dict[str, Any],
    lead_text: str,
    chars_per_second: float,
    pre_title_pause: float,
) -> tuple[float, int]:
    hook = str(script.get("hook") or "")
    if not hook:
        raise ValueError("script 缺少 hook，无法按开头文案估算书名时码")
    before_title_han = han_count(hook) + han_count(lead_text)
    if before_title_han <= 0:
        raise ValueError("书名前汉字数必须大于 0")
    first_word_start = float(script.get("first_word_start_estimate_seconds") or 0.0)
    return first_word_start + before_title_han / chars_per_second + pre_title_pause, before_title_han


def choose_card_count(total_frames: int, min_card_frames: int, max_card_frames: int) -> int:
    minimum_count = math.ceil(total_frames / max_card_frames)
    maximum_count = total_frames // min_card_frames
    if minimum_count > maximum_count:
        raise ValueError(
            f"轮播区间 {total_frames} 帧无法拆成每张 {min_card_frames}–{max_card_frames} 帧"
        )
    return minimum_count


def distribute_frames(total_frames: int, card_count: int, min_card_frames: int) -> list[int]:
    extra = total_frames - card_count * min_card_frames
    frames: list[int] = []
    for index in range(card_count):
        before = math.floor(index * extra / card_count)
        after = math.floor((index + 1) * extra / card_count)
        frames.append(min_card_frames + (after - before))
    if sum(frames) != total_frames:
        raise AssertionError("逐卡帧数分配未覆盖完整轮播区间")
    return frames


def build_plan(
    *,
    title_start: float,
    carousel_start: float,
    fps: int,
    target_cover_lead_frames: int,
    min_card_frames: int,
    max_card_frames: int,
    minimum_cards: int,
) -> dict[str, Any]:
    carousel_start_frame = round(carousel_start * fps)
    title_start_frame = round(title_start * fps)
    target_cover_start_frame = title_start_frame - target_cover_lead_frames
    total_frames = target_cover_start_frame - carousel_start_frame
    card_count = choose_card_count(total_frames, min_card_frames, max_card_frames)
    if card_count < minimum_cards:
        raise ValueError(
            f"轮播只能容纳 {card_count} 张，低于最低 {minimum_cards} 张；应调整开头结构或轮播起点"
        )
    card_frames = distribute_frames(total_frames, card_count, min_card_frames)
    if any(value > max_card_frames for value in card_frames):
        raise AssertionError("逐卡帧数超过允许上限")
    return {
        "carousel_start_frame": carousel_start_frame,
        "title_start_frame": title_start_frame,
        "target_cover_start_frame": target_cover_start_frame,
        "total_carousel_frames": total_frames,
        "card_count": card_count,
        "card_frames": card_frames,
    }


def available_cover_count(manifest: dict[str, Any], manifest_path: Path, target_title: str) -> int:
    target = normalize_title(target_title)
    count = 0
    for item in manifest.get("covers", []):
        if not isinstance(item, dict):
            continue
        title = item.get("titleZh") or item.get("title")
        source = manifest_path.parent / str(item.get("file") or "")
        if normalize_title(title) != target and source.is_file():
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="按开头文案或真实配音时码规划书封轮播")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--script", type=Path, help="配音前估算使用的 script-vNNN.json")
    parser.add_argument("--timing", type=Path, help="配音后最终规划使用的 timing-vNNN.json")
    parser.add_argument("--title-start-seconds", type=float, help="可选；实测书名首字起声时码")
    parser.add_argument("--cover-manifest", type=Path, help="可选；校验非目标真实书封是否足够")
    parser.add_argument("--target-title", default="")
    parser.add_argument("--lead-text", default="今天分享的是")
    parser.add_argument("--chars-per-second", type=float, default=4.56)
    parser.add_argument("--pre-title-pause", type=float, default=0.55)
    parser.add_argument("--carousel-start", type=float, default=2.90)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--target-cover-lead-frames", type=int, default=0)
    parser.add_argument("--min-card-frames", type=int, default=3)
    parser.add_argument("--max-card-frames", type=int, default=4)
    parser.add_argument("--minimum-cards", type=int, default=6)
    parser.add_argument("--version", default="v001")
    args = parser.parse_args()

    if args.fps <= 0 or args.chars_per_second <= 0:
        parser.error("fps 和 chars-per-second 必须大于 0")
    if args.min_card_frames <= 0 or args.max_card_frames < args.min_card_frames:
        parser.error("逐卡帧数范围无效")
    if args.title_start_seconds is None and not args.timing and not args.script:
        parser.error("至少提供 --title-start-seconds、--timing 或 --script")

    source = "script_estimated"
    title_start: float | None = None
    before_title_han: int | None = None
    timing_source: str | None = None
    if args.title_start_seconds is not None:
        title_start = args.title_start_seconds
        source = "voice_actual"
        timing_source = "cli_measured_title_start"
    elif args.timing:
        timing_path = args.timing.expanduser().resolve()
        title_start = actual_title_start(read_json(timing_path))
        if title_start is not None:
            source = "voice_actual"
            timing_source = str(timing_path)
    if title_start is None:
        if not args.script:
            raise SystemExit("timing 缺少 book_title_delivery.title_start_seconds，且没有 script 可供估算")
        script_path = args.script.expanduser().resolve()
        title_start, before_title_han = estimated_title_start(
            read_json(script_path), args.lead_text, args.chars_per_second, args.pre_title_pause
        )
        timing_source = str(script_path)

    geometry = build_plan(
        title_start=title_start,
        carousel_start=args.carousel_start,
        fps=args.fps,
        target_cover_lead_frames=args.target_cover_lead_frames,
        min_card_frames=args.min_card_frames,
        max_card_frames=args.max_card_frames,
        minimum_cards=args.minimum_cards,
    )
    carousel_start_frame = geometry["carousel_start_frame"]
    title_start_frame = geometry["title_start_frame"]
    target_cover_start_frame = geometry["target_cover_start_frame"]
    total_frames = geometry["total_carousel_frames"]
    card_count = geometry["card_count"]
    card_frames = geometry["card_frames"]

    available = None
    if args.cover_manifest:
        manifest_path = args.cover_manifest.expanduser().resolve()
        available = available_cover_count(read_json(manifest_path), manifest_path, args.target_title)
        if available < card_count:
            raise SystemExit(
                f"真实书封库只有 {available} 张非目标封面，但当前声音时码需要 {card_count} 张；"
                "请扩充书封库，禁止提前展示目标封面"
            )

    carousel_start = carousel_start_frame / args.fps
    carousel_end = target_cover_start_frame / args.fps
    plan = {
        "version": args.version,
        "mode": "voice_timing_derived",
        "timing_source_type": source,
        "timing_source": timing_source,
        "needs_actual_timing_replan": source != "voice_actual",
        "estimate_formula": "(hook_han + lead_text_han) / chars_per_second + pre_title_pause",
        "before_title_han_count": before_title_han,
        "chars_per_second": args.chars_per_second,
        "pre_title_pause_seconds": args.pre_title_pause,
        "fps": args.fps,
        "carousel_start_frame": carousel_start_frame,
        "title_start_frame": title_start_frame,
        "target_cover_start_frame": target_cover_start_frame,
        "carousel_start": round(carousel_start, 6),
        "carousel_end": round(carousel_end, 6),
        "title_start_seconds": round(title_start_frame / args.fps, 6),
        "target_cover_lead_frames": args.target_cover_lead_frames,
        "target_cover_lead_seconds": round(args.target_cover_lead_frames / args.fps, 6),
        "total_carousel_frames": total_frames,
        "card_count": card_count,
        "card_frames": card_frames,
        "card_durations": [round(value / args.fps, 6) for value in card_frames],
        "card_frame_range": [args.min_card_frames, args.max_card_frames],
        "available_non_target_covers": available,
        "insufficient_library_policy": "block_expand_library",
        "target_title": args.target_title,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

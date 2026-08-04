#!/usr/bin/env python3
"""Render the opening picture track while keeping the real cover until body speech."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

import cv2


WIDTH, HEIGHT, FPS = 1080, 1440, 30


def build_frame_plan(opening: dict, fps: int = FPS) -> list[str]:
    flash_end = round(float(opening.get("target_flash_end", 0.1)) * fps)
    carousel_start = round(float(opening["carousel_start"]) * fps)
    carousel_end = round(float(opening["carousel_end"]) * fps)
    cover_start = round(float(opening["target_cover_hold_start"]) * fps)
    body_start = math.ceil(float(opening["body_voice_start"]) * fps)
    wave = opening["waterdrop_lock_response"]
    wave_start = round(float(wave["visual_start"]) * fps)
    wave_end = round(float(wave["visual_end"]) * fps)
    hero_cut_at = opening.get("hero_cut_at", wave.get("hero_cut_at"))

    if carousel_end != cover_start:
        raise ValueError("carousel_end 必须与 target_cover_hold_start 同帧")
    if hero_cut_at is not None and float(hero_cut_at) < float(opening["body_voice_start"]) - (1 / fps):
        raise ValueError("hero_cut_at 不得早于 body_voice_start")
    if not (cover_start <= wave_start < wave_end <= body_start):
        raise ValueError("水波必须完整发生在真实书封保持区间")

    plan: list[str] = []
    for frame in range(body_start):
        if frame < flash_end:
            role = "target_flash"
        elif frame < carousel_start:
            role = "masked_keyword"
        elif frame < carousel_end:
            role = "carousel"
        elif wave_start <= frame < wave_end:
            role = "waterwave"
        else:
            role = "target_cover"
        plan.append(role)
    return plan


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def open_capture(path: Path) -> cv2.VideoCapture:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise FileNotFoundError(path)
    return capture


def read_frame(capture: cv2.VideoCapture, frame_index: int, source: Path):
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = capture.read()
    if not ok:
        raise RuntimeError(f"素材在第 {frame_index} 帧提前结束：{source}")
    return cv2.resize(frame, (WIDTH, HEIGHT), interpolation=cv2.INTER_CUBIC)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--opening", type=Path, required=True)
    parser.add_argument("--carousel-video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    project = args.project.resolve()
    opening_path = args.opening if args.opening.is_absolute() else project / args.opening
    carousel_path = args.carousel_video if args.carousel_video.is_absolute() else project / args.carousel_video
    output = args.output if args.output.is_absolute() else project / args.output
    if output.exists():
        raise FileExistsError(f"版本文件已存在，不覆盖：{output}")

    opening = read_json(opening_path)
    plan = build_frame_plan(opening)
    flash_path = project / opening["target_hero_asset"]
    mask_path = project / opening["masked_keyword_video_asset"]
    target_path = project / opening["target_cover_title_page_asset"]
    wave_path = project / opening["waterdrop_lock_response"]["effect_asset"]
    target = cv2.imread(str(target_path), cv2.IMREAD_COLOR)
    if target is None:
        raise FileNotFoundError(target_path)
    target = cv2.resize(target, (WIDTH, HEIGHT), interpolation=cv2.INTER_LANCZOS4)

    captures = {
        "target_flash": (open_capture(flash_path), flash_path),
        "masked_keyword": (open_capture(mask_path), mask_path),
        "carousel": (open_capture(carousel_path), carousel_path),
        "waterwave": (open_capture(wave_path), wave_path),
    }
    starts = {
        "target_flash": 0,
        "masked_keyword": round(float(opening.get("target_flash_end", 0.1)) * FPS),
        "carousel": round(float(opening["carousel_start"]) * FPS),
        "waterwave": round(float(opening["waterdrop_lock_response"]["visual_start"]) * FPS),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    encoder = subprocess.Popen(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{WIDTH}x{HEIGHT}",
            "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "fast",
            "-crf", "18", "-pix_fmt", "yuv420p", str(output),
        ],
        stdin=subprocess.PIPE,
    )
    try:
        for frame_index, role in enumerate(plan):
            if role == "target_cover":
                frame = target
            else:
                capture, source = captures[role]
                frame = read_frame(capture, frame_index - starts[role], source)
            encoder.stdin.write(frame.tobytes())
    finally:
        encoder.stdin.close()
        for capture, _ in captures.values():
            capture.release()
    if encoder.wait() != 0:
        raise RuntimeError("片头画面编码失败")
    print(f"{output} ({len(plan)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

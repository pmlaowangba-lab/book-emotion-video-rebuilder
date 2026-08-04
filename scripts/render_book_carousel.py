#!/usr/bin/env python3
"""把动态数量书封卡渲染为逐卡 snap-settle 视频。"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np


WIDTH, HEIGHT, FPS = 1080, 1440, 30


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_frame(path: Path) -> np.ndarray:
    frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if frame is None:
        raise FileNotFoundError(path)
    return cv2.resize(frame, (WIDTH, HEIGHT), interpolation=cv2.INTER_LANCZOS4)


def resolve_asset(record_path: Path, value: str) -> Path:
    asset = Path(value).expanduser()
    if asset.is_absolute():
        return asset
    project_relative = (record_path.parents[2] / asset).resolve()
    if project_relative.is_file():
        return project_relative
    return (record_path.parent / asset).resolve()


def snap_settle(frame: np.ndarray, index: int, frame_count: int) -> np.ndarray:
    progress = index / max(1, frame_count - 1)
    eased = 1.0 - (1.0 - progress) ** 3
    scale = 1.035 + (1.0 - 1.035) * eased
    width, height = round(WIDTH * scale), round(HEIGHT * scale)
    zoomed = cv2.resize(frame, (width, height), interpolation=cv2.INTER_CUBIC)
    x = (width - WIDTH) // 2
    y = (height - HEIGHT) // 2
    settled = zoomed[y:y + HEIGHT, x:x + WIDTH]
    blur = 1.5 * (1.0 - eased)
    if blur >= 0.35:
        kernel = max(3, int(round(blur * 4)) | 1)
        settled = cv2.GaussianBlur(settled, (kernel, kernel), blur)
    return settled


def overlay_rgba(frame: np.ndarray, layer: np.ndarray | None) -> np.ndarray:
    if layer is None:
        return frame
    alpha = layer[:, :, 3:4].astype(np.float32) / 255.0
    color = layer[:, :, :3].astype(np.float32)
    return np.clip(frame.astype(np.float32) * (1.0 - alpha) + color * alpha, 0, 255).astype(np.uint8)


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染书封轮播 snap-settle 视频")
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--caption-overlay", type=Path)
    args = parser.parse_args()

    record_path = args.record.expanduser().resolve()
    record = read_json(record_path)
    cards = record.get("cards", [])
    if not cards or len(cards) != int(record.get("card_count") or 0):
        raise SystemExit("轮播记录的 cards 与 card_count 不一致")

    caption = None
    if args.caption_overlay:
        caption = cv2.imread(str(args.caption_overlay.expanduser().resolve()), cv2.IMREAD_UNCHANGED)
        if caption is None or caption.shape[2] != 4:
            raise SystemExit("--caption-overlay 必须是 1080×1440 RGBA PNG")
        caption = cv2.resize(caption, (WIDTH, HEIGHT), interpolation=cv2.INTER_LANCZOS4)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoder = subprocess.Popen([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(args.output),
    ], stdin=subprocess.PIPE)
    assert encoder.stdin is not None
    expected_frames = 0
    for card in cards:
        frame_count = int(card.get("frames") or 0)
        if frame_count not in {3, 4}:
            raise SystemExit(f"单卡帧数必须是 3 或 4：{frame_count}")
        source = read_frame(resolve_asset(record_path, str(card.get("asset") or "")))
        for local_index in range(frame_count):
            frame = snap_settle(source, local_index, frame_count)
            encoder.stdin.write(overlay_rgba(frame, caption).tobytes())
        expected_frames += frame_count
    encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError("书封轮播编码失败")
    print(f"{args.output} ({expected_frames} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

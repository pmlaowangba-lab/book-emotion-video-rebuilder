#!/usr/bin/env python3
"""Create a same-page book lock still and full-frame waterwave clip.

The title, real cover, opening subtitle and background are baked into one page
before displacement, so every visible layer bends together at the water-drop cue.
"""

from __future__ import annotations

import argparse
import math
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1440, 30


def add_centered_text(frame: np.ndarray, text: str, font_path: Path, size: int, y: int, opacity: int = 255) -> np.ndarray:
    rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = ImageFont.truetype(str(font_path), size)
    bounds = draw.textbbox((0, 0), text, font=font)
    x = (W - (bounds[2] - bounds[0])) // 2
    draw.rounded_rectangle((x - 18, y - 8, x + (bounds[2] - bounds[0]) + 18, y + size + 20), radius=16, fill=(0, 0, 0, 105))
    draw.text((x + 5, y + 5), text, font=font, fill=(0, 0, 0, min(210, opacity)))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, opacity))
    rgba.alpha_composite(layer)
    return cv2.cvtColor(np.asarray(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)


def ripple(frame: np.ndarray, progress: float) -> np.ndarray:
    grid_y, grid_x = np.indices((H, W), dtype=np.float32)
    dx = grid_x - W / 2
    dy = grid_y - H / 2
    radius = np.sqrt(dx * dx + dy * dy) + 1.0
    strength = math.sin(math.pi * progress) ** 0.88
    phase = radius * 0.038 - progress * math.tau * 1.55
    displacement = 6.0 * strength * np.sin(phase)
    map_x = grid_x + displacement * dx / radius + 0.9 * strength * np.sin(grid_y * 0.024 + progress * 6.0)
    map_y = grid_y + displacement * dy / radius + 1.2 * strength * np.sin(grid_x * 0.021 - progress * 5.4)
    return cv2.remap(frame, map_x, map_y, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-page", type=Path, required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--subtitle", required=True)
    parser.add_argument("--output-page", type=Path, required=True)
    parser.add_argument("--output-video", type=Path, required=True)
    parser.add_argument("--output-caption-layer", type=Path)
    parser.add_argument("--duration", type=float, default=0.4)
    args = parser.parse_args()

    frame = cv2.imread(str(args.source_page.resolve()), cv2.IMREAD_COLOR)
    if frame is None:
        raise FileNotFoundError(args.source_page)
    frame = cv2.resize(frame, (W, H), interpolation=cv2.INTER_LANCZOS4)
    frame = add_centered_text(frame, args.subtitle, args.font.resolve(), 60, 1155)
    args.output_page.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.output_page), frame):
        raise RuntimeError("锁书同页定帧写入失败")
    if args.output_caption_layer:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        font = ImageFont.truetype(str(args.font.resolve()), 60)
        bounds = draw.textbbox((0, 0), "今天分享的是", font=font)
        x = (W - (bounds[2] - bounds[0])) // 2
        draw.rounded_rectangle((x - 18, 1147, x + (bounds[2] - bounds[0]) + 18, 1235), radius=16, fill=(0, 0, 0, 105))
        draw.text((x + 5, 1160), "今天分享的是", font=font, fill=(0, 0, 0, 210))
        draw.text((x, 1155), "今天分享的是", font=font, fill=(255, 255, 255, 255))
        args.output_caption_layer.parent.mkdir(parents=True, exist_ok=True)
        layer.save(args.output_caption_layer)

    frame_count = math.ceil(args.duration * FPS)
    encoder = subprocess.Popen([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", str(args.output_video),
    ], stdin=subprocess.PIPE)
    assert encoder.stdin is not None
    for index in range(frame_count):
        encoder.stdin.write(ripple(frame, index / max(1, frame_count - 1)).tobytes())
    encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError("整页水波编码失败")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

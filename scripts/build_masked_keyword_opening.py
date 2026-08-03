#!/usr/bin/env python3
"""Render the fixed same-source keyword mask and horizontal reveal opening clip."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHINESE_FONT = SKILL_ROOT / "assets/fonts/杨任东竹石体-Heavy.ttf"


WIDTH = 1080
HEIGHT = 1440
FPS = 30
DURATION = 2.8
KEYWORD_END = 1.25
LINE_END = 1.35


def font_path(family: str) -> Path:
    result = subprocess.run(
        ["fc-match", "-f", "%{file}\n", family],
        check=True,
        capture_output=True,
        text=True,
    )
    path = Path(result.stdout.splitlines()[0]).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"找不到字体 {family}: {path}")
    return path


def cover_frame(frame: np.ndarray) -> np.ndarray:
    height, width = frame.shape[:2]
    scale = max(WIDTH / width, HEIGHT / height)
    resized = cv2.resize(frame, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_LANCZOS4)
    y = max(0, (resized.shape[0] - HEIGHT) // 2)
    x = max(0, (resized.shape[1] - WIDTH) // 2)
    return resized[y : y + HEIGHT, x : x + WIDTH].copy()


def fit_font(text: str, path: Path, max_width: int, start_size: int) -> ImageFont.FreeTypeFont:
    size = start_size
    while size >= 36:
        font = ImageFont.truetype(str(path), size=size)
        box = font.getbbox(text, stroke_width=max(1, size // 70))
        if box[2] - box[0] <= max_width:
            return font
        size -= 4
    raise ValueError(f"文字过长，无法排版: {text}")


def render_keyword_mask(keyword: str, keyword_font: Path | None, custom_mask: Path | None) -> np.ndarray:
    if custom_mask is not None:
        image = Image.open(custom_mask).convert("L")
        if image.size != (WIDTH, HEIGHT):
            raise ValueError(f"自定义关键词蒙版必须是 {WIDTH}×{HEIGHT}，当前是 {image.width}×{image.height}")
        mask = np.asarray(image)
        if np.count_nonzero(mask > 16) < 1000:
            raise ValueError("自定义关键词蒙版几乎全黑，没有可用字形")
        return mask

    if keyword_font is None:
        raise ValueError("未提供关键词字体或自定义蒙版")
    keyword_image = Image.new("L", (WIDTH, HEIGHT), 0)
    keyword_draw = ImageDraw.Draw(keyword_image)
    keyword_size = 320
    keyword_face = fit_font(keyword, keyword_font, 960, keyword_size)
    keyword_box = keyword_draw.textbbox((0, 0), keyword, font=keyword_face, stroke_width=4)
    keyword_width = keyword_box[2] - keyword_box[0]
    keyword_height = keyword_box[3] - keyword_box[1]
    keyword_xy = ((WIDTH - keyword_width) // 2 - keyword_box[0], 735 - keyword_height // 2 - keyword_box[1])
    keyword_draw.text(keyword_xy, keyword, font=keyword_face, fill=255, stroke_width=4, stroke_fill=255)
    return np.asarray(keyword_image)


def render_hook(hook: str, hook_font: Path) -> np.ndarray:
    hook_image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    hook_draw = ImageDraw.Draw(hook_image)
    lines = [line.strip() for line in hook.split("\n") if line.strip()]
    if not lines:
        raise ValueError("情绪钩子不得为空")
    if len(lines) > 2:
        raise ValueError("情绪钩子最多两行")
    hook_face = fit_font(max(lines, key=len), hook_font, 840, 58)
    top = 255
    for line in lines:
        box = hook_draw.textbbox((0, 0), line, font=hook_face)
        width = box[2] - box[0]
        hook_draw.text(((WIDTH - width) // 2, top), line, font=hook_face, fill=(255, 255, 255, 255))
        top += 76

    return cv2.cvtColor(np.asarray(hook_image), cv2.COLOR_RGBA2BGRA)


def ease_in_cubic(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * value


def compose(frame: np.ndarray, index: int, keyword_mask: np.ndarray, hook_layer: np.ndarray) -> np.ndarray:
    time = index / FPS
    result = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    alpha = keyword_mask.astype(np.float32)[:, :, None] / 255.0
    result = (frame.astype(np.float32) * alpha).astype(np.uint8)

    hook_alpha = hook_layer[:, :, 3:4].astype(np.float32) / 255.0
    hook_rgb = hook_layer[:, :, :3].astype(np.float32)
    result = (result.astype(np.float32) * (1.0 - hook_alpha) + hook_rgb * hook_alpha).astype(np.uint8)

    if time >= KEYWORD_END:
        if time < LINE_END:
            progress = (time - KEYWORD_END) / (LINE_END - KEYWORD_END)
            half_width = round((40 + (WIDTH / 2 - 40) * progress))
            half_height = 2
        else:
            progress = ease_in_cubic((time - LINE_END) / (DURATION - LINE_END))
            half_width = WIDTH // 2
            half_height = round(2 + (HEIGHT / 2 - 2) * progress)
        x1 = max(0, WIDTH // 2 - half_width)
        x2 = min(WIDTH, WIDTH // 2 + half_width)
        y1 = max(0, HEIGHT // 2 - half_height)
        y2 = min(HEIGHT, HEIGHT // 2 + half_height)
        result[y1:y2, x1:x2] = frame[y1:y2, x1:x2]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="生成毛笔关键词同源视频遮罩片段")
    parser.add_argument(
        "--bridge-video",
        required=True,
        type=Path,
        help="必须是 08A-片头遮罩素材 中独立生成的 mask-source-vNNN.mp4",
    )
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--hook", required=True, help="最多两行，使用 \\n 分隔")
    parser.add_argument(
        "--hide-hook",
        action="store_true",
        help="遮罩段只显示两字关键词，不在遮罩上叠加完整 Hook",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--keyword-font", type=Path)
    parser.add_argument(
        "--keyword-mask",
        type=Path,
        help="可选的 1080×1440 黑底白字毛笔蒙版；最终交付优先使用，提供后忽略 --keyword-font",
    )
    parser.add_argument(
        "--content-mask-record",
        type=Path,
        help="第一阶段 mask-keyword-vNNN.json；新项目必须提供且状态为 confirmed",
    )
    parser.add_argument("--hook-font", type=Path)
    parser.add_argument("--version", default="v001")
    args = parser.parse_args()

    keyword = args.keyword.strip()
    if not re.fullmatch(r"[\u3400-\u9fff]{2}", keyword):
        raise ValueError("遮罩关键词必须且只能是两个汉字")
    if not re.fullmatch(r"v\d{3}", args.version):
        raise ValueError("version 必须符合 vNNN")

    bridge = args.bridge_video.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not bridge.is_file():
        raise FileNotFoundError(f"桥段视频不存在: {bridge}")
    if "08A-片头遮罩素材" not in bridge.parts:
        raise ValueError("桥段视频必须位于 08A-片头遮罩素材，禁止复用正文视频")
    if {"08-正文画面", "09-Grok视频"}.intersection(bridge.parts):
        raise ValueError("桥段视频不得引用正文图片或正文 Grok 视频路径")
    if output.exists():
        raise FileExistsError(f"不覆盖已有片头，请升级版本: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    custom_mask = args.keyword_mask.expanduser().resolve() if args.keyword_mask else None
    if custom_mask is not None and not custom_mask.is_file():
        raise FileNotFoundError(f"自定义关键词蒙版不存在: {custom_mask}")
    content_mask_record = args.content_mask_record.expanduser().resolve() if args.content_mask_record else None
    content_mask_approved = False
    if content_mask_record is not None:
        if not content_mask_record.is_file():
            raise FileNotFoundError(f"第一阶段遮罩记录不存在: {content_mask_record}")
        if "02-情绪提炼" not in content_mask_record.parts:
            raise ValueError("第一阶段遮罩记录必须位于 02-情绪提炼")
        record = json.loads(content_mask_record.read_text(encoding="utf-8"))
        record_mask_value = Path(str(record.get("alpha_mask") or "")).expanduser()
        record_mask = record_mask_value.resolve() if record_mask_value.is_absolute() else (content_mask_record.parents[1] / record_mask_value).resolve()
        if record.get("review_status") != "confirmed":
            raise ValueError("第一阶段遮罩尚未确认，禁止进入片头生产")
        if record.get("keyword") != keyword or record.get("han_count") != 2:
            raise ValueError("片头关键词与第一阶段确认的两字遮罩不一致")
        if custom_mask is None or record_mask != custom_mask:
            raise ValueError("--keyword-mask 必须直接引用第一阶段已确认的 alpha_mask")
        content_mask_approved = True
    keyword_font = None if custom_mask else (args.keyword_font or font_path("Kaiti SC")).expanduser().resolve()
    hook_font = (args.hook_font or DEFAULT_CHINESE_FONT).expanduser().resolve()
    normalized_hook = re.sub(r"\\+n", "\n", args.hook)
    keyword_mask = render_keyword_mask(keyword, keyword_font, custom_mask)
    hook_layer = (
        np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
        if args.hide_hook
        else render_hook(normalized_hook, hook_font)
    )

    mask_output = output.with_name(f"keyword-mask-{args.version}.png")
    metadata_output = output.with_name(f"masked-keyword-expand-{args.version}.json")
    if mask_output.exists() or metadata_output.exists():
        raise FileExistsError("关键词遮罩或元数据已存在，请升级版本")
    Image.fromarray(keyword_mask).save(mask_output)

    capture = cv2.VideoCapture(str(bridge))
    if not capture.isOpened():
        raise RuntimeError(f"无法打开桥段视频: {bridge}")
    source_fps = capture.get(cv2.CAP_PROP_FPS) or FPS
    source_frames = max(1, int(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
    writer = subprocess.Popen(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(output),
        ],
        stdin=subprocess.PIPE,
    )
    try:
        total_frames = round(DURATION * FPS)
        for index in range(total_frames):
            source_index = round((index / FPS) * source_fps) % source_frames
            capture.set(cv2.CAP_PROP_POS_FRAMES, source_index)
            ok, frame = capture.read()
            if not ok:
                capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = capture.read()
            if not ok:
                raise RuntimeError("桥段视频无可读帧")
            result = compose(cover_frame(frame), index, keyword_mask, hook_layer)
            assert writer.stdin is not None
            writer.stdin.write(result.tobytes())
    finally:
        capture.release()
        if writer.stdin:
            writer.stdin.close()
    return_code = writer.wait()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg 生成片头失败，退出码 {return_code}")

    metadata = {
        "schema_version": 2,
        "template": "masked_book_carousel",
        "version": args.version,
        "mask_source_video": str(bridge),
        "source_role": "opening_mask_only",
        "output": str(output),
        "keyword_mask": str(mask_output),
        "keyword_mask_source": str(custom_mask) if custom_mask else str(keyword_font),
        "keyword_mask_style": "custom_reviewed" if content_mask_approved else ("custom_review_required" if custom_mask else "kaiti_preview_fallback"),
        "content_mask_record": str(content_mask_record) if content_mask_record else None,
        "keyword": keyword,
        "hook": normalized_hook,
        "hook_visible_on_mask": not args.hide_hook,
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS},
        "duration": DURATION,
        "keyword_hold_end_local": KEYWORD_END,
        "line_end_local": LINE_END,
        "expand_end_local": DURATION,
        "same_source_video": True,
    }
    metadata_output.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Render a versioned review MP4 with the current emotional-book opening rules."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1440, 30
SKILL_ROOT = Path(__file__).resolve().parents[1]
TARGET_COVER_HOLD_START = 4.10
WATERWAVE_EFFECT_START = 4.45
WATERWAVE_TRIGGER = 4.45
TARGET_LOCK_START = 4.85
TARGET_LOCK_END = 5.55
TITLE_DROP_SETTLE_FRAMES = 21
FONT_CHINESE = str(SKILL_ROOT / "assets/fonts/杨任东竹石体-Heavy.ttf")
FONT_GEORGIA = "/System/Library/Fonts/Supplemental/Georgia.ttf"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def read_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def cover_fill(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    scale = max(W / w, H / h)
    resized = cv2.resize(image, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_LANCZOS4)
    y = (resized.shape[0] - H) // 2
    x = (resized.shape[1] - W) // 2
    return resized[y:y + H, x:x + W].copy()


def target_cover_card(cover: np.ndarray) -> np.ndarray:
    bg = cv2.GaussianBlur(cover_fill(cover), (0, 0), 26)
    bg = cv2.convertScaleAbs(bg, alpha=0.78, beta=24)
    h, w = cover.shape[:2]
    target_h = 790
    target_w = round(target_h * w / h)
    clear = cv2.resize(cover, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
    x, y = (W - target_w) // 2, (H - target_h) // 2 + 36
    glow = np.zeros_like(bg)
    cv2.rectangle(glow, (x - 9, y - 9), (x + target_w + 9, y + target_h + 9), (255, 255, 255), -1)
    glow = cv2.GaussianBlur(glow, (0, 0), 12)
    bg = cv2.addWeighted(bg, 1.0, glow, 0.25, 0)
    bg[y:y + target_h, x:x + target_w] = clear
    return bg


def zoom_center(image: np.ndarray, scale: float, pan_x: float = 0, pan_y: float = 0) -> np.ndarray:
    nh, nw = round(H * scale), round(W * scale)
    resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_CUBIC)
    x = max(0, min(nw - W, round((nw - W) / 2 + pan_x)))
    y = max(0, min(nh - H, round((nh - H) / 2 + pan_y)))
    return resized[y:y + H, x:x + W].copy()


def ease_out(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return 1 - (1 - p) ** 3


def smoothstep(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return p * p * (3.0 - 2.0 * p)


def single_breath_scale(progress: float, peak_at: float = 0.60) -> float:
    if progress <= peak_at:
        q = smoothstep(progress / peak_at)
        return 1.005 + (1.030 - 1.005) * q
    q = smoothstep((progress - peak_at) / (1.0 - peak_at))
    return 1.030 + (1.022 - 1.030) * q


def text_layer(text: str, font_path: str, size: int, fill: tuple[int, ...], y: int,
               stroke: int = 0, stroke_fill: tuple[int, ...] = (0, 0, 0, 120),
               shadow_offset: int = 0, font_index: int = 0) -> np.ndarray:
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(font_path, size, index=font_index)
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    x = (W - (box[2] - box[0])) // 2
    if shadow_offset:
        draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 175))
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return cv2.cvtColor(np.array(canvas), cv2.COLOR_RGBA2BGRA)


def blend_overlay(frame: np.ndarray, overlay: np.ndarray, opacity: float = 1.0) -> np.ndarray:
    alpha = overlay[:, :, 3:4].astype(np.float32) / 255.0 * opacity
    color = overlay[:, :, :3].astype(np.float32)
    return np.clip(frame.astype(np.float32) * (1 - alpha) + color * alpha, 0, 255).astype(np.uint8)


def apply_page_water_ripple(frame: np.ndarray, local_time: float) -> np.ndarray:
    """Deform the entire page like a water surface; never draw a visible ring overlay."""
    duration = TARGET_LOCK_START - WATERWAVE_EFFECT_START
    if local_time < 0 or local_time >= duration:
        return frame
    progress = max(0.0, min(1.0, local_time / duration))
    grid_y, grid_x = np.indices((H, W), dtype=np.float32)
    dx = grid_x - W / 2
    dy = grid_y - H / 2
    radius = np.sqrt(dx * dx + dy * dy) + 1.0
    strength = math.sin(math.pi * progress) ** 0.88
    # Use a broad, low-amplitude displacement field.  The reference reads as the
    # page becoming a water surface, not as a ring graphic placed on top of it.
    phase = radius * 0.038 - progress * math.tau * 1.55
    radial_displacement = 6.0 * strength * np.sin(phase)
    unit_x = dx / radius
    unit_y = dy / radius
    surface_x = 0.9 * strength * np.sin(grid_y * 0.024 + progress * 6.0)
    surface_y = 1.2 * strength * np.sin(grid_x * 0.021 - progress * 5.4)
    map_x = grid_x + radial_displacement * unit_x + surface_x
    map_y = grid_y + radial_displacement * unit_y + surface_y
    return cv2.remap(frame, map_x, map_y, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101)


def write_page_water_ripple_asset(path: Path, page: np.ndarray) -> None:
    if path.exists():
        raise FileExistsError(f"整页水波素材已存在，不覆盖：{path}")
    duration = TARGET_LOCK_START - WATERWAVE_EFFECT_START
    frame_count = math.ceil(duration * FPS)
    encoder = subprocess.Popen([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", str(path),
    ], stdin=subprocess.PIPE)
    for index in range(frame_count):
        frame = apply_page_water_ripple(page, index / FPS)
        encoder.stdin.write(frame.tobytes())
    encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError("整页水波素材编码失败")


def target_lock_frame(hero: np.ndarray, t: float) -> np.ndarray:
    bg = hero.copy()
    local_frame = max(0, round((t - TARGET_LOCK_START) * FPS))
    if local_frame == 0:
        return bg
    progress = min(1.0, local_frame / TITLE_DROP_SETTLE_FRAMES)
    settle = ease_out(progress)
    scale = 1.85 + (1.0 - 1.85) * settle
    title_y = round(520 + (70 - 520) * settle)
    opacity = 0.42 if local_frame == 1 else 1.0
    blur = max(0.0, 2.5 * (1.0 - min(1.0, local_frame / 8.0)))
    title = text_layer("《乌合之众》", FONT_CHINESE, round(88 * scale), (255, 255, 255, 255), title_y, 0, shadow_offset=5)
    if blur > 0:
        title = cv2.GaussianBlur(title, (0, 0), blur)
    bg = blend_overlay(bg, title, opacity)
    author_progress = smoothstep((local_frame - 13) / 6.0)
    if author_progress > 0:
        author = text_layer("古斯塔夫·勒庞", FONT_CHINESE, 44, (245, 245, 245, 245), 190, 0, shadow_offset=4)
        bg = blend_overlay(bg, author, author_progress)
    return bg


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--source-timeline", type=Path)
    parser.add_argument("--cover", type=Path)
    parser.add_argument("--version", default="v005")
    args = parser.parse_args()
    project = args.project.resolve()
    version = args.version
    if not version.startswith("v") or not version[1:].isdigit():
        raise ValueError("--version 必须是 vNNN")
    source_timeline = (args.source_timeline or project / "11-时间轴/timeline-v004.json").resolve()
    timeline = json.loads(source_timeline.read_text(encoding="utf-8"))
    duration = float(timeline["duration"])
    if args.cover:
        cover_path = args.cover.resolve()
    else:
        cover_candidates = sorted(
            path for path in (project / "01-书籍资料").glob("cover-v*.*")
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        )
        if not cover_candidates:
            raise FileNotFoundError("未找到 cover-vNNN 封面素材")
        cover_path = cover_candidates[-1]

    out_dir = project / "12-预览"
    opening_dir = project / f"10-片头字幕/{version}"
    opening_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    silent = out_dir / f"timeline-picture-{version}.mp4"
    final = out_dir / f"timeline-preview-{version}.mp4"
    opening_preview = out_dir / f"opening-preview-{version}.mp4"
    opening_json = project / f"10-片头字幕/opening-{version}.json"
    waterwave_effect_asset = opening_dir / f"waterwave-page-refraction-{version}.mp4"
    for path in (silent, final, opening_preview, opening_json, waterwave_effect_asset, project / f"11-时间轴/timeline-{version}.json"):
        if path.exists():
            raise FileExistsError(f"版本文件已存在，不覆盖：{path}")

    cover = read_image(cover_path)
    body = [cover_fill(read_image(project / f"08-正文画面/v002/shot-{i:02d}.png")) for i in range(1, 5)]
    target_cover = target_cover_card(cover)
    target_cover_asset = opening_dir / f"target-cover-hold-{version}.png"
    cv2.imwrite(str(target_cover_asset), target_cover)
    write_page_water_ripple_asset(waterwave_effect_asset, target_cover)
    cards = [cover_fill(read_image(project / card["asset"])) for card in timeline["opening"]["carousel_cards"]]
    card_durations = timeline["opening"]["card_durations"]
    bridge = cv2.VideoCapture(str(project / timeline["opening"]["masked_keyword_video_asset"]))
    target_hero_rel = "10-片头字幕/v002/target-hero-v002.mp4"
    target_hero = cv2.VideoCapture(str(project / target_hero_rel))
    ok, target_hero_first = target_hero.read()
    if not ok:
        raise RuntimeError("目标主画面视频无法读取")
    target_hero_first = cv2.resize(target_hero_first, (W, H), interpolation=cv2.INTER_CUBIC)
    target_hero.set(cv2.CAP_PROP_POS_FRAMES, 0)

    header_title = text_layer("《乌合之众》", FONT_CHINESE, 88, (255, 255, 255, 255), 70, 0, shadow_offset=5)
    header_author = text_layer("古斯塔夫·勒庞", FONT_CHINESE, 44, (245, 245, 245, 245), 190, 0, shadow_offset=4)
    caption_layers: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for cap in timeline["captionTrack"]:
        zh = text_layer(cap["zh"], FONT_CHINESE, 60, (255, 255, 255, 255), 1050, 0, shadow_offset=5)
        en = text_layer(cap["en"], FONT_GEORGIA, 32, (245, 245, 245, 235), 1150, 0, shadow_offset=3)
        caption_layers[cap["id"]] = (zh, en)

    ffmpeg = subprocess.Popen([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(silent)
    ], stdin=subprocess.PIPE)

    scene_ranges = [(5.55, 18.55), (18.35, 27.9), (27.5, 37.7), (37.3, duration)]
    total_frames = math.ceil(duration * FPS)
    for frame_index in range(total_frames):
        t = frame_index / FPS
        if t < 0.1:
            frame = blend_overlay(target_hero_first.copy(), header_title)
            frame = blend_overlay(frame, header_author)
        elif t < 2.9:
            ok, frame = bridge.read()
            if not ok:
                bridge.set(cv2.CAP_PROP_POS_MSEC, (t - 0.1) * 1000)
                ok, frame = bridge.read()
            frame = cv2.resize(frame, (W, H), interpolation=cv2.INTER_CUBIC) if ok else body[0].copy()
        elif t < TARGET_COVER_HOLD_START:
            local = t - 2.9
            elapsed = 0.0
            card_index = len(cards) - 1
            progress = 1.0
            for idx, card_duration in enumerate(card_durations):
                if local < elapsed + card_duration:
                    card_index = idx
                    progress = (local - elapsed) / card_duration
                    break
                elapsed += card_duration
            scale = 1.035 - 0.035 * ease_out(progress)
            frame = zoom_center(cards[card_index], scale)
            blur = max(0.0, 1.5 * (1 - progress))
            if blur > 0.15:
                frame = cv2.GaussianBlur(frame, (0, 0), blur)
        elif t < TARGET_LOCK_START:
            frame = target_cover.copy()
            if t >= WATERWAVE_EFFECT_START:
                local_wave_time = t - WATERWAVE_EFFECT_START
                frame = apply_page_water_ripple(frame, local_wave_time)
        elif t < TARGET_LOCK_END:
            target_hero.set(cv2.CAP_PROP_POS_MSEC, (t - TARGET_LOCK_START) * 1000)
            ok, hero_frame = target_hero.read()
            if not ok:
                hero_frame = target_hero_first.copy()
            else:
                hero_frame = cv2.resize(hero_frame, (W, H), interpolation=cv2.INTER_CUBIC)
            frame = target_lock_frame(hero_frame, t)
        else:
            scene_idx = 3
            for idx, (start, end) in enumerate(scene_ranges):
                if start <= t < end:
                    scene_idx = idx
                    break
            start, end = scene_ranges[scene_idx]
            p = min(1.0, max(0.0, (t - start) / (end - start)))
            scale = single_breath_scale(p)
            pan = -4 + 8 * smoothstep(p)
            frame = zoom_center(body[scene_idx], scale, pan_x=pan if scene_idx % 2 == 0 else -pan)
            for cut, incoming in [(18.35, 1), (27.5, 2), (37.3, 3)]:
                if cut <= t < cut + 0.4:
                    q = (t - cut) / 0.4
                    ins, ine = scene_ranges[incoming]
                    ip = max(0.0, (t - ins) / (ine - ins))
                    incoming_frame = zoom_center(body[incoming], single_breath_scale(min(1.0, ip)))
                    frame = cv2.addWeighted(frame, 1 - q, incoming_frame, q, 0)
                    break
            frame = blend_overlay(frame, header_title)
            frame = blend_overlay(frame, header_author)
            for cap in timeline["captionTrack"]:
                if float(cap["start"]) <= t < float(cap["end"]):
                    zh, en = caption_layers[cap["id"]]
                    frame = blend_overlay(frame, zh)
                    frame = blend_overlay(frame, en)
                    break
        ffmpeg.stdin.write(frame.tobytes())
    ffmpeg.stdin.close()
    if ffmpeg.wait() != 0:
        raise RuntimeError("FFmpeg video render failed")
    bridge.release()
    target_hero.release()

    click_sfx = Path(__file__).resolve().parent.parent / "assets/sfx-library/jianying-carousel-clockwork-v001.mp3"
    water_sfx = Path(__file__).resolve().parent.parent / "assets/sfx-library/jianying-book-lock-waterdrop-v001.mp3"
    project_click_sfx = project / f"06-配乐音效/sfx-carousel-clockwork-{version}.mp3"
    project_water_sfx = project / f"06-配乐音效/sfx-book-lock-waterdrop-{version}.mp3"
    if project_click_sfx.exists() or project_water_sfx.exists():
        raise FileExistsError(f"目标音效版本已存在：{version}")
    shutil.copyfile(click_sfx, project_click_sfx)
    shutil.copyfile(water_sfx, project_water_sfx)
    mix = project / f"06-配乐音效/audio-mix-preview-{version}.wav"
    if mix.exists():
        raise FileExistsError(f"目标混音版本已存在：{mix}")
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(project / "05-配音/voice-v002.wav"),
        "-i", str(project / "06-配乐音效/bgm-v004.wav"),
        "-i", str(click_sfx),
        "-i", str(water_sfx),
        "-filter_complex",
        "[0:a]volume=1.0[v];[1:a]volume=1.58[b];"
        "[2:a]atrim=start=0.083:end=1.216,asetpts=PTS-STARTPTS,afade=t=out:st=1.093:d=0.04,adelay=2942|2942,volume=0.55[c];"
        f"[3:a]adelay={round(WATERWAVE_TRIGGER * 1000)}|{round(WATERWAVE_TRIGGER * 1000)},volume=0.58[w];"
        "[v][b][c][w]amix=inputs=4:duration=longest:normalize=0,"
        "loudnorm=I=-7:LRA=3:TP=-1,"
        "loudnorm=I=-9.7:LRA=3:TP=-2,"
        "volume='if(lt(t\\,16)\\,0.84\\,if(lt(t\\,40)\\,1\\,0.89))':eval=frame,"
        "volume=0.5dB,volume=3.1dB[a]",
        "-map", "[a]", "-ar", "48000", "-ac", "2", str(mix)
    ])
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(silent), "-i", str(mix),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
        "-af", "aresample=44100:first_pts=0", "-c:a", "aac", "-profile:a", "aac_low",
        "-b:a", "256k", "-ar", "44100", "-ac", "2", "-disposition:a:0", "default",
        "-metadata:s:a:0", "language=zho", "-metadata:s:a:0", "title=主声音轨",
        "-metadata:s:a:0", "handler_name=SoundHandler",
        "-t", f"{duration:.3f}", "-movflags", "+faststart", str(final)
    ])
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(final), "-t", "6.2",
        "-c:v", "copy", "-c:a", "copy", str(opening_preview)
    ])

    new_timeline = timeline
    new_timeline["version"] = version
    new_timeline["typography"] = {
        "chinese_font_id": "yrdzst-heavy",
        "chinese_font_asset": "assets/fonts/杨任东竹石体-Heavy.ttf",
        "title_px": 88,
        "author_px": 44,
        "zh_caption_px": 60,
        "english_font_family": "Georgia",
        "en_caption_px": 32,
    }
    new_timeline["opening"]["carousel_motion"] = {"type": "snap_settle", "scale_start": 1.035, "scale_end": 1.0, "soft_focus_px": 1.5, "transition": "hard_cut"}
    new_timeline["opening"]["target_lock_start"] = TARGET_LOCK_START
    new_timeline["opening"]["target_lock_end"] = TARGET_LOCK_END
    new_timeline["opening"]["target_cover_hold_start"] = TARGET_COVER_HOLD_START
    new_timeline["opening"]["target_cover_hold_end"] = TARGET_LOCK_START
    new_timeline["opening"]["target_cover_source"] = str(cover_path.relative_to(project))
    new_timeline["opening"]["target_cover_hold_asset"] = str(target_cover_asset.relative_to(project))
    new_timeline["opening"]["target_lock_mode"] = "cover_waterwave_then_title_drop"
    new_timeline["opening"].pop("target_cover_asset", None)
    new_timeline["opening"]["target_hero_asset"] = target_hero_rel
    new_timeline["opening"]["title_motion"] = {
        "type": "waterdrop_title_drop",
        "settle_frames": TITLE_DROP_SETTLE_FRAMES,
        "easing": "ease_out_cubic",
        "start_anchor": "center",
        "end_anchor": "top",
    }
    new_timeline["opening"].pop("water_visual_effect", None)
    new_timeline["opening"]["waterdrop_lock_response"] = {
        "type": "cover_waterwave_then_title_drop",
        "effect_on": "entire_page",
        "effect_style": "full_frame_displacement_map",
        "effect_scope": "entire_page",
        "effect_asset": str(waterwave_effect_asset.relative_to(project)),
        "visual_start": WATERWAVE_EFFECT_START,
        "wave_trigger_at": WATERWAVE_TRIGGER,
        "sfx_at": WATERWAVE_TRIGGER,
        "visual_end": TARGET_LOCK_START,
        "hero_cut_at": TARGET_LOCK_START,
        "literal_water_graphic": False,
        "overlay_graphic": False,
        "visible_ring": False,
        "page_deformation": True,
        "refraction": True,
        "perceptible_motion": True,
        "title_keyframes": [
            {"frame": 0, "scale": 1.85, "opacity": 0.0, "blur_px": 2.5, "y_px": 520, "transform_y": 0.0},
            {"frame": 1, "scale": 1.73, "opacity": 0.42, "blur_px": 2.2, "y_px": 458, "transform_y": -0.11},
            {"frame": 2, "scale": 1.63, "opacity": 1.0, "blur_px": 1.9, "y_px": 405, "transform_y": -0.20},
            {"frame": 6, "scale": 1.31, "opacity": 1.0, "blur_px": 0.0, "y_px": 233, "transform_y": -0.51},
            {"frame": 13, "scale": 1.05, "opacity": 1.0, "blur_px": 0.0, "y_px": 97, "transform_y": -0.75},
            {"frame": 21, "scale": 1.0, "opacity": 1.0, "blur_px": 0.0, "y_px": 70, "transform_y": -0.79},
        ],
        "author_keyframes": [
            {"frame": 0, "scale": 1.0, "opacity": 0.0, "transform_y": -0.67},
            {"frame": 13, "scale": 1.0, "opacity": 0.0, "transform_y": -0.67},
            {"frame": 19, "scale": 1.0, "opacity": 1.0, "transform_y": -0.67},
        ],
    }
    for item in new_timeline["openingTrack"]:
        if item["id"].startswith("carousel-"):
            item["motion"] = {"type": "snap_settle", "scale_start": 1.035, "scale_end": 1.0, "soft_focus_px": 1.5}
        if item["id"] == "target-lock":
            item["start"] = TARGET_LOCK_START
            item["end"] = TARGET_LOCK_END
            item["asset"] = target_hero_rel
            item["transition_in"] = "hard_cut"
            item["motion"] = {"type": "grok_video", "scale_start": 1.0, "scale_end": 1.0, "pan_x": 0, "pan_y": 0}
            item["title_motion"] = new_timeline["opening"]["title_motion"]
    new_timeline["openingTrack"] = [item for item in new_timeline["openingTrack"] if item.get("id") not in {"target-lock-water-fx", "target-cover-waterdrop-fx", "target-cover-waterwave-fx", "target-cover-waterwave-page", "target-cover-hold"}]
    new_timeline["openingTrack"].append({
        "id": "target-cover-hold", "start": TARGET_COVER_HOLD_START, "end": TARGET_LOCK_START,
        "asset": str(target_cover_asset.relative_to(project)), "transition_in": "hard_cut", "transition_out": "hard_cut",
        "motion": {"type": "snap_settle", "scale_start": 1.02, "scale_end": 1.0, "soft_focus_px": 0.5},
    })
    new_timeline["openingTrack"].append({
        "id": "target-cover-waterwave-page",
        "start": WATERWAVE_EFFECT_START,
        "end": TARGET_LOCK_START,
        "wave_trigger_at": WATERWAVE_TRIGGER,
        "asset": str(waterwave_effect_asset.relative_to(project)),
        "layer": "page_effect",
        "effect_on": "entire_page",
        "motion": {"type": "full_frame_displacement_map", "page_deformation": True, "overlay_graphic": False, "visible_ring": False},
    })
    new_timeline["openingTrack"].sort(key=lambda item: float(item["start"]))
    motion_pattern = [
        {"type": "zoom_in", "scale_start": 1.0, "scale_end": 1.12, "pan_x_ratio": 0.0, "pan_y_ratio": 0.0},
        {"type": "pan_left", "scale_start": 1.10, "scale_end": 1.10, "pan_x_ratio": -0.03, "pan_y_ratio": 0.0},
        {"type": "zoom_out", "scale_start": 1.12, "scale_end": 1.0, "pan_x_ratio": 0.0, "pan_y_ratio": 0.0},
        {"type": "pan_right", "scale_start": 1.10, "scale_end": 1.10, "pan_x_ratio": 0.03, "pan_y_ratio": 0.0},
        {"type": "emotional_hold", "scale_start": 1.0, "scale_end": 1.025, "pan_x_ratio": 0.0, "pan_y_ratio": 0.0},
    ]
    container = {"coverage": "full_canvas", "overflow": "hidden", "fit": "cover", "transform_target": "inner_image"}
    for index, scene in enumerate(new_timeline["sceneTrack"]):
        if scene.get("motion", {}).get("type") != "grok_video":
            scene["motion"] = {**motion_pattern[index % len(motion_pattern)], "interpolation": "cubic_ease_in_out", "sample_per_frame": True, "container": container}
    transitions = []
    for index, scene in enumerate(new_timeline["sceneTrack"][1:], start=1):
        segment_ids = {str(value) for value in scene.get("script_segment_ids", [])}
        strong_turn = any("cognitive" in value or "reversal" in value for value in segment_ids)
        boundary = float(scene["voice_start"])
        duration_value = 0.0 if strong_turn else 0.2
        transitions.append({
            "from": new_timeline["sceneTrack"][index - 1]["id"],
            "to": scene["id"],
            "start": boundary - duration_value / 2,
            "end": boundary + duration_value / 2,
            "duration": duration_value,
            "type": "hard_cut" if strong_turn else "short_fade",
            "reason": "strong_turn" if strong_turn else "emotional_continuity",
        })
    if len(transitions) >= 3 and not any(item["type"] == "hard_cut" for item in transitions):
        pivot = len(transitions) // 2
        boundary = float(new_timeline["sceneTrack"][pivot + 1]["voice_start"])
        transitions[pivot].update({"start": boundary, "end": boundary, "duration": 0.0, "type": "hard_cut", "reason": "strong_turn"})
    new_timeline["transitionTrack"] = transitions
    for cap in new_timeline["captionTrack"]:
        cap["reveal_end"] = cap["start"]
        cap["display_mode"] = "segment"
    new_timeline["audioTrack"] = [
        {"id": "voice-v002", "type": "voice", "start": 0.0, "end": duration, "asset": "05-配音/voice-v002.wav", "volume": 1.0},
        {"id": f"bgm-{version}", "type": "bgm", "start": 0.0, "end": duration, "asset": "06-配乐音效/bgm-v004.wav", "volume": 1.58, "lyrics": True, "usage_scope": "local_preview_only"},
        {"id": f"sfx-carousel-clockwork-{version}", "type": "sfx", "start": 2.942, "end": 4.075, "asset": str(project_click_sfx.relative_to(project)), "source_start": 0.083, "volume": 0.55},
        {"id": f"sfx-book-lock-waterdrop-{version}", "type": "sfx", "start": WATERWAVE_TRIGGER, "end": WATERWAVE_TRIGGER + 1.595, "asset": str(project_water_sfx.relative_to(project)), "volume": 0.58},
    ]
    new_timeline["bookMeta"]["start"] = TARGET_LOCK_START
    new_timeline["bookMeta"]["cover"] = str(cover_path.relative_to(project))
    new_timeline["preview"] = f"12-预览/timeline-preview-{version}.mp4"
    opening_json.write_text(json.dumps(new_timeline["opening"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (project / f"11-时间轴/timeline-{version}.json").write_text(json.dumps(new_timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(final)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""把情绪读书时间轴写成可编辑剪映草稿。"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_VIDEOCUT_ROOT = Path(
    os.environ.get("VIDEOCUT_ROOT", str(Path(__file__).resolve().parents[2] / "videocut"))
)
SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHINESE_FONT = SKILL_ROOT / "assets" / "fonts" / "杨任东竹石体-Heavy.ttf"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def seconds(value: float) -> str:
    text = f"{max(0.0, float(value)):.3f}".rstrip("0").rstrip(".")
    return f"{text or '0'}s"


def resolve_asset(project: Path, value: str) -> Path:
    path = Path(value).expanduser()
    path = path if path.is_absolute() else project / path
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"素材不存在：{path}")
    return path


def media_duration_seconds(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def sampled_times(duration: float, fps: int = 30) -> list[float]:
    frames = max(1, math.ceil(duration * fps))
    values = [min(duration, index / fps) for index in range(frames + 1)]
    if values[-1] != duration:
        values.append(duration)
    return values


def localize_remaining_media(draft_path: Path, ensure_entries: Any, patch_size: Any) -> dict[str, str]:
    """补齐 videocut 当前未本地化的音频等素材。"""
    content_path = draft_path / "draft_content.json"
    content = read_json(content_path)
    media_dir = draft_path / "Resources" / "local_media"
    media_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    for materials in content.get("materials", {}).values():
        if not isinstance(materials, list):
            continue
        for material in materials:
            if not isinstance(material, dict):
                continue
            original_value = material.get("path")
            if not isinstance(original_value, str) or not original_value:
                continue
            original = Path(original_value).expanduser()
            if not original.is_file():
                continue
            try:
                original.resolve().relative_to(draft_path)
                continue
            except ValueError:
                pass
            material_id = material.get("id") or material.get("material_id") or original.stem
            target = media_dir / f"{material_id}{original.suffix.lower()}"
            if not target.exists() or target.stat().st_size != original.stat().st_size:
                shutil.copy2(original, target)
            material["path"] = str(target)
            if "media_path" in material:
                material["media_path"] = str(target)
            copied[original_value] = str(target)
    if copied:
        content_path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
        ensure_entries(draft_path)
    total_size = sum(path.stat().st_size for path in media_dir.glob("*") if path.is_file())
    patch_size(draft_path, total_size)
    return copied


def package_local_font(draft_path: Path) -> Path:
    """把默认中文字体随草稿打包；当前库不支持任意 TTF 自动绑定。"""
    if not DEFAULT_CHINESE_FONT.is_file():
        raise FileNotFoundError(f"默认中文字体不存在：{DEFAULT_CHINESE_FONT}")
    font_dir = draft_path / "Resources" / "local_fonts"
    font_dir.mkdir(parents=True, exist_ok=True)
    target = font_dir / DEFAULT_CHINESE_FONT.name
    if not target.exists() or target.stat().st_size != DEFAULT_CHINESE_FONT.stat().st_size:
        shutil.copy2(DEFAULT_CHINESE_FONT, target)
    return target


def add_visual_segment(script: Any, draft: Any, project: Path, item: dict[str, Any], track: str) -> None:
    start = float(item["start"])
    end = float(item["end"])
    duration = end - start
    if duration <= 0:
        raise ValueError(f"画面片段时长无效：{item.get('id')}")
    asset = resolve_asset(project, str(item["asset"]))
    motion = item.get("motion", {})
    segment = draft.VideoSegment(
        str(asset),
        draft.trange(seconds(start), seconds(duration)),
        source_timerange=draft.trange("0s", seconds(duration)) if asset.suffix.lower() in {".mp4", ".mov", ".m4v", ".webm"} else None,
        clip_settings=draft.ClipSettings(),
    )

    motion_type = motion.get("type")
    if motion_type in {"micro_zoom_in", "micro_zoom_out"}:
        segment.add_keyframe(draft.KeyframeProperty.uniform_scale, "0s", float(motion.get("scale_start", 1.0)))
        segment.add_keyframe(draft.KeyframeProperty.uniform_scale, seconds(duration), float(motion.get("scale_end", 1.0)))
    elif motion_type == "micro_pan":
        pan_x = float(motion.get("pan_x", 0)) / 1080.0
        pan_y = float(motion.get("pan_y", 0)) / 1440.0
        prop = draft.KeyframeProperty.position_x if pan_x else draft.KeyframeProperty.position_y
        value = pan_x or pan_y
        segment.add_keyframe(prop, "0s", 0.0)
        segment.add_keyframe(prop, seconds(duration), value)
    elif motion_type in {"zoom_in", "zoom_out", "pan_left", "pan_right", "emotional_hold"}:
        scale_start = float(motion.get("scale_start", 1.0))
        scale_end = float(motion.get("scale_end", 1.0))
        pan_x_ratio = float(motion.get("pan_x_ratio", 0.0))
        pan_y_ratio = float(motion.get("pan_y_ratio", 0.0))
        for moment in sampled_times(duration):
            progress = 0.0 if duration == 0 else moment / duration
            eased = smoothstep(progress)
            scale = scale_start + (scale_end - scale_start) * eased
            segment.add_keyframe(draft.KeyframeProperty.uniform_scale, seconds(moment), scale)
            if pan_x_ratio:
                segment.add_keyframe(draft.KeyframeProperty.position_x, seconds(moment), pan_x_ratio * eased)
            if pan_y_ratio:
                segment.add_keyframe(draft.KeyframeProperty.position_y, seconds(moment), pan_y_ratio * eased)
    elif motion_type in {"smooth_single_breath", "smooth_push_in"}:
        scale_start = float(motion.get("scale_start", 1.005))
        scale_end = float(motion.get("scale_end", 1.022))
        scale_peak = float(motion.get("scale_peak", scale_end))
        peak_at = float(motion.get("peak_at", 0.60))
        pan_x = float(motion.get("pan_x", 0)) / 1080.0
        pan_y = float(motion.get("pan_y", 0)) / 1440.0
        pan_prop = draft.KeyframeProperty.position_x if pan_x else draft.KeyframeProperty.position_y
        pan_value = pan_x or pan_y
        for moment in sampled_times(duration):
            progress = 0.0 if duration == 0 else moment / duration
            if motion_type == "smooth_single_breath":
                if progress <= peak_at:
                    local = smoothstep(progress / peak_at)
                    scale = scale_start + (scale_peak - scale_start) * local
                else:
                    local = smoothstep((progress - peak_at) / (1.0 - peak_at))
                    scale = scale_peak + (scale_end - scale_peak) * local
            else:
                scale = scale_start + (scale_end - scale_start) * smoothstep(progress)
            segment.add_keyframe(draft.KeyframeProperty.uniform_scale, seconds(moment), scale)
            if pan_value:
                segment.add_keyframe(pan_prop, seconds(moment), (-0.5 + smoothstep(progress)) * pan_value)

    fade = min(float(item.get("transition_duration", 0.2)), duration / 4)
    if item.get("transition_in") in {"crossfade", "short_fade"}:
        segment.add_keyframe(draft.KeyframeProperty.alpha, "0s", 0.0)
        segment.add_keyframe(draft.KeyframeProperty.alpha, seconds(fade), 1.0)
    if item.get("transition_out") in {"crossfade", "short_fade"}:
        segment.add_keyframe(draft.KeyframeProperty.alpha, seconds(max(0.0, duration - fade)), 1.0)
        segment.add_keyframe(draft.KeyframeProperty.alpha, seconds(duration), 0.0)
    script.add_segment(segment, track)


def add_text_segment(
    script: Any,
    draft: Any,
    item: dict[str, Any],
    *,
    key: str,
    track: str,
    size: float,
    transform_y: float,
    alpha: float = 1.0,
    font: Any | None = None,
    title_snap: dict[str, Any] | None = None,
    keyframes_key: str = "title_keyframes",
) -> None:
    text = str(item.get(key, "")).strip()
    if not text:
        return
    start = float(item["start"])
    end = float(item["end"])
    if end <= start:
        raise ValueError(f"文字片段时长无效：{item.get('id')}")
    segment = draft.TextSegment(
        text,
        draft.trange(seconds(start), seconds(end - start)),
        font=font,
        style=draft.TextStyle(size=size, bold=False, color=(1.0, 1.0, 1.0), alpha=alpha, align=1),
        border=draft.TextBorder(width=2, color=(0.0, 0.0, 0.0), alpha=0.18),
        shadow=draft.TextShadow(alpha=0.42, color=(0.0, 0.0, 0.0), diffuse=12, distance=3, angle=-40),
        clip_settings=draft.ClipSettings(transform_y=transform_y),
    )
    if title_snap:
        for keyframe in title_snap.get(keyframes_key, []):
            moment = float(keyframe.get("frame", 0)) / 30.0
            if moment > end - start:
                continue
            segment.add_keyframe(
                draft.KeyframeProperty.uniform_scale,
                seconds(moment),
                float(keyframe.get("scale", 1.0)),
            )
            segment.add_keyframe(
                draft.KeyframeProperty.alpha,
                seconds(moment),
                float(keyframe.get("opacity", 1.0)),
            )
            if "transform_y" in keyframe:
                segment.add_keyframe(
                    draft.KeyframeProperty.position_y,
                    seconds(moment),
                    float(keyframe["transform_y"]),
                )
    script.add_segment(segment, track)


def add_audio_segment(script: Any, draft: Any, project: Path, item: dict[str, Any], track: str) -> None:
    start = float(item.get("start", 0))
    end = float(item["end"])
    if end <= start:
        raise ValueError(f"音频片段时长无效：{item.get('id')}")
    asset = resolve_asset(project, str(item["asset"]))
    duration = end - start
    source_duration = media_duration_seconds(asset)
    effective_duration = min(duration, source_duration)
    if effective_duration <= 0:
        raise ValueError(f"音频素材时长无效：{item.get('id')}")
    segment = draft.AudioSegment(
        str(asset),
        draft.trange(seconds(start), seconds(effective_duration)),
        source_timerange=draft.trange("0s", seconds(effective_duration)),
        volume=float(item.get("volume", 1.0)),
    )
    fade_in = float(item.get("fade_in", 0))
    fade_out = float(item.get("fade_out", 0))
    if fade_in or fade_out:
        segment.add_fade(seconds(fade_in), seconds(fade_out))
    script.add_segment(segment, track)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 1080×1440 可编辑剪映草稿")
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--timeline", required=True, type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--draft-root", type=Path)
    parser.add_argument("--videocut-root", type=Path, default=DEFAULT_VIDEOCUT_ROOT)
    args = parser.parse_args()

    project = args.project.expanduser().resolve()
    timeline_path = args.timeline.expanduser().resolve()
    videocut_root = args.videocut_root.expanduser().resolve()
    if not (project / "manifest.json").is_file():
        raise SystemExit("项目缺少 manifest.json")
    if not timeline_path.is_file():
        raise SystemExit(f"时间轴不存在：{timeline_path}")
    sys.path.insert(0, str(videocut_root / "src"))

    try:
        import pyJianYingDraft as draft
        from short_video_auto_editor.jianying_experiment import (
            ensure_current_jianying_entry_files,
            localize_media_files,
            patch_material_size_metadata,
            patch_generated_metadata,
            resolve_jianying_draft_root,
        )
    except ModuleNotFoundError as exc:
        raise SystemExit("请使用 videocut/.venv/bin/python 运行，当前环境缺少 pyJianYingDraft") from exc

    timeline = read_json(timeline_path)
    canvas = timeline.get("canvas", {})
    if (canvas.get("width"), canvas.get("height"), canvas.get("fps")) != (1080, 1440, 30):
        raise SystemExit("时间轴必须是 1080×1440@30fps")
    duration = float(timeline.get("duration", 0))
    if duration <= 0:
        raise SystemExit("时间轴缺少有效 duration")

    draft_root = resolve_jianying_draft_root(args.draft_root)
    folder = draft.DraftFolder(str(draft_root))
    if folder.has_draft(args.name):
        raise SystemExit(f"剪映草稿已存在，不覆盖：{args.name}")
    script = folder.create_draft(args.name, 1080, 1440, fps=30, allow_replace=False)

    tracks = [
        (draft.TrackType.video, "opening_visual_a", 0),
        (draft.TrackType.video, "opening_visual_b", 1),
        (draft.TrackType.video, "opening_fx", 2),
        (draft.TrackType.video, "body_visual_a", 3),
        (draft.TrackType.video, "body_visual_b", 4),
        (draft.TrackType.audio, "voice", 0),
        (draft.TrackType.audio, "bgm", 1),
        (draft.TrackType.audio, "sfx", 2),
        (draft.TrackType.text, "book_title", 600),
        (draft.TrackType.text, "book_author", 610),
        (draft.TrackType.text, "zh_captions", 900),
        (draft.TrackType.text, "en_captions", 910),
    ]
    for track_type, name, index in tracks:
        script.add_track(track_type, name, relative_index=index)

    for index, item in enumerate(timeline.get("openingTrack", [])):
        track = "opening_fx" if item.get("layer") in {"effect", "page_effect"} else f"opening_visual_{'a' if index % 2 == 0 else 'b'}"
        add_visual_segment(script, draft, project, item, track)
    transition_in = {
        str(item.get("to")): item
        for item in timeline.get("transitionTrack", [])
        if isinstance(item, dict)
    }
    transition_out = {
        str(item.get("from")): item
        for item in timeline.get("transitionTrack", [])
        if isinstance(item, dict)
    }
    for index, item in enumerate(timeline.get("sceneTrack", [])):
        scene_item = dict(item)
        incoming = transition_in.get(str(item.get("id")))
        outgoing = transition_out.get(str(item.get("id")))
        if incoming and incoming.get("type") == "short_fade":
            scene_item["transition_in"] = "short_fade"
            scene_item["transition_duration"] = float(incoming.get("duration", 0.2))
        if outgoing and outgoing.get("type") == "short_fade":
            scene_item["transition_out"] = "short_fade"
            scene_item["transition_duration"] = float(outgoing.get("duration", 0.2))
        add_visual_segment(script, draft, project, scene_item, f"body_visual_{'a' if index % 2 == 0 else 'b'}")
    for item in timeline.get("audioTrack", []):
        kind = str(item.get("type", ""))
        if kind not in {"voice", "bgm", "sfx"}:
            raise ValueError(f"不支持的音频轨类型：{kind}")
        add_audio_segment(script, draft, project, item, kind)
    for item in timeline.get("captionTrack", []):
        add_text_segment(
            script,
            draft,
            item,
            key="zh",
            track="zh_captions",
            size=12.5,
            transform_y=0.54,
            font=draft.FontType.SourceHanSerifCN_SemiBold,
        )
        add_text_segment(
            script,
            draft,
            item,
            key="en",
            track="en_captions",
            size=6.2,
            transform_y=0.66,
            alpha=0.78,
            font=draft.FontType.Cormorant_Garamond_Medium,
        )
    book_meta = timeline.get("bookMeta") or {}
    opening = timeline.get("opening", {})
    title_snap = opening.get("waterdrop_lock_response")
    if not isinstance(title_snap, dict) or title_snap.get("type") not in {"hard_cut_title_drop", "cover_waterdrop_then_title_drop", "cover_waterwave_then_title_drop"}:
        title_snap = None
    if book_meta:
        title_binding = opening.get("target_cover_title_binding", {})
        same_page_title = title_binding.get("mode") == "same_page_as_cover" and isinstance(title_snap, dict)
        if same_page_title:
            wave_start = float(title_snap["visual_start"])
            wave_end = float(title_snap["visual_end"])
            title_start = float(title_binding["title_start"])
            pre_wave_title = {**book_meta, "start": title_start, "end": wave_start}
            post_wave_title = {**book_meta, "start": wave_end}
            add_text_segment(
                script,
                draft,
                pre_wave_title,
                key="title",
                track="book_title",
                size=18.0,
                transform_y=-0.79,
                font=draft.FontType.SourceHanSerifCN_Bold,
                title_snap=title_snap,
            )
            add_text_segment(
                script,
                draft,
                post_wave_title,
                key="title",
                track="book_title",
                size=18.0,
                transform_y=-0.79,
                font=draft.FontType.SourceHanSerifCN_Bold,
            )
            author_meta = {**book_meta, "start": max(wave_end, float(opening.get("target_lock_start", wave_end)))}
        else:
            add_text_segment(
                script,
                draft,
                book_meta,
                key="title",
                track="book_title",
                size=18.0,
                transform_y=-0.79,
                font=draft.FontType.SourceHanSerifCN_Bold,
                title_snap=title_snap,
            )
            author_meta = book_meta
        add_text_segment(
            script,
            draft,
            author_meta,
            key="author",
            track="book_author",
            size=8.0,
            transform_y=-0.67,
            alpha=0.86,
            font=draft.FontType.SourceHanSerifCN_Regular,
            title_snap=None if same_page_title else title_snap,
            keyframes_key="author_keyframes",
        )

    script.save()
    draft_path = draft_root / args.name
    localized_font = package_local_font(draft_path)
    patch_generated_metadata(draft_path, draft_root, args.name, duration)
    localized = localize_media_files(draft_path)
    localized.update(
        localize_remaining_media(
            draft_path,
            ensure_current_jianying_entry_files,
            patch_material_size_metadata,
        )
    )
    report = {
        "draft_name": args.name,
        "project": str(project),
        "timeline": str(timeline_path),
        "duration": duration,
        "canvas": canvas,
        "tracks": [name for _, name, _ in tracks],
        "localized_media": localized,
        "typography": timeline.get("typography", {}),
        "localized_font_asset": str(localized_font),
        "font_binding": "requires_jianying_local_font_activation",
        "delivery_profile": "1080p_3x4_editable",
        "video_master": str((project / str(timeline.get("preview", ""))).resolve()),
        "same_timeline_as_video_master": True,
        "final_deliverable": "jianying_draft",
        "flattened_final_mp4": False,
    }
    report_path = draft_path / "book_emotion_draft_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    version_match = re.search(r"(v\d{3})", timeline_path.stem)
    version = version_match.group(1) if version_match else "v001"
    pointer_dir = project / "13-剪映草稿"
    pointer_dir.mkdir(exist_ok=True)
    pointer_path = pointer_dir / f"draft-{version}.json"
    pointer_path.write_text(
        json.dumps(
            {
                "draft_name": args.name,
                "draft_path": str(draft_path),
                "draft_content": str(draft_path / "draft_content.json"),
                "draft_meta_info": str(draft_path / "draft_meta_info.json"),
                "report": str(report_path),
                "localized_font_asset": str(localized_font),
                "font_binding": "requires_jianying_local_font_activation",
                "delivery_profile": "1080p_3x4_editable",
                "video_master": str((project / str(timeline.get("preview", ""))).resolve()),
                "same_timeline_as_video_master": True,
                "final_deliverable": "jianying_draft",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"draft_path": str(draft_path), "report": str(report_path), "pointer": str(pointer_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

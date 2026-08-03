#!/usr/bin/env python3
"""把旧技术步骤清单合并为 schema 8 的六个内部状态节点。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GROUPS = {
    "content_package": ["content_package"],
    "sound_package": ["sound_design", "voice", "music_sfx"],
    "visual_package": ["storyboard", "grok_video", "opening"],
    "timeline_package": ["subtitles", "timeline"],
    "final_video": ["final_video"],
    "jianying_draft": ["jianying_draft"],
}

DEFAULT_VOICE = {
    "provider": "volcengine",
    "speaker": "S_Bkoh3uBT1",
    "selection_mode": "default",
    "speed_mode": "reference_locked",
    "reference_video_id": "7668678283642779072",
    "provider_speech_rate": 10,
    "target_chars_per_second": 4.56,
    "tolerance_chars_per_second": 0.02,
}

DEFAULT_CONTENT = {
    # 迁移旧项目时显式保留 v1；新项目的 v2 两字遮罩契约不得被降级。
    "contract_version": 1,
    "entry_mode": "direct_theme",
    "max_script_seconds": 60.0,
    "preferred_han_count": [245, 268],
    "target_han_count": 256,
    "max_han_count": 270,
    "segment_han_targets": {
        "hook": 14,
        "book_lead": 12,
        "viewer_expression": 46,
        "pressure_escalation": 54,
        "cognitive_reversal": 62,
        "action_permission": 36,
        "identity_close": 32,
    },
    "duration_override": None,
    "forbidden_confirmation_openings": [
        "你是不是也这样",
        "你有没有发现",
        "你是否也",
        "有没有过这种时候",
        "你是不是经常",
    ],
}

IMAGE_PROVIDERS = ["codex_imagegen", "grok_local", "apimart"]
DEFAULT_IMAGE_GENERATION = {
    "provider": "codex_imagegen",
    "selection_mode": "default",
    "override_reason": None,
    "fallback_provider": "grok_local",
    "allowed_providers": IMAGE_PROVIDERS,
    "generation_mode": "parallel_individual",
    "batch_strategy": "parallel_all",
    "wait_policy": "wait_after_all_submitted",
    "preferred_image_size": [1536, 2048],
    "minimum_image_size": [1080, 1440],
    "retry_mode": "parallel_failed_only",
    "max_retry_batches": 1,
    "serial_waits_allowed": 0,
}
DEFAULT_VIDEO_GENERATION = {
    "provider": "grok_cli",
    "bridge": "grok-local",
    "model": "grok-imagine-video-via-cli",
    "mode": "reference_to_video",
    "auth_mode": "membership_oauth_only",
    "motion_profile": "restrained_micro_motion",
    "selection_mode": "default",
}
DEFAULT_TYPOGRAPHY = {
    "chinese_font_id": "yrdzst-heavy",
    "chinese_font_asset": "assets/fonts/杨任东竹石体-Heavy.ttf",
    "english_font_family": "Georgia",
}
DEFAULT_PARALLEL_PIPELINE = {
    "mode": "event_driven_dag_after_content_lock",
    "content_lock_required": True,
    "scheduler": "dependency_ready_queue",
    "resource_groups": ["voice", "body_visual", "opening", "subtitle_music"],
    "dispatch_policy": "dispatch_when_dependencies_completed",
    "progression_policy": "advance_each_asset_immediately",
    "image_to_video_trigger": "per_image_qc_pass",
    "pre_join_timing_basis": "script_estimated",
    "final_timing_basis": "voice_actual",
    "join_policy": "final_assembly_waits_only_for_declared_dependencies",
    "failure_scope": "descendants_only",
    "max_ready_queue_delay_seconds": 30,
    "progress_reporting": {
        "mode": "event_driven_realtime",
        "refresh_on_every_transition": True,
        "heartbeat_seconds": 60,
        "json_output": "07-分镜/progress-state-v001.json",
        "markdown_output": "07-分镜/progress-v001.md",
    },
    "paired_review_steps": ["sound_package", "visual_package"],
}
DEFAULT_DELIVERY = {
    "profile": "1080p_3x4_editable",
    "video_master": {
        "width": 1080,
        "height": 1440,
        "fps": 30,
        "video_codec": "h264",
        "pixel_format": "yuv420p",
        "audio_codec": "aac",
        "audio_sample_rate": 48000,
        "audio_channels": 2,
    },
    "jianying_draft": {
        "required": True,
        "same_timeline_required": True,
        "editable_tracks_required": True,
        "flattened_mp4_only": False,
    },
}


def ensure_defaults(manifest: dict[str, Any]) -> bool:
    """补齐 schema 8 的生产默认值，并启用独立图片并行生图。"""
    defaults = manifest.setdefault("defaults", {})
    changed = False
    if defaults.get("voice") != DEFAULT_VOICE:
        defaults["voice"] = DEFAULT_VOICE.copy()
        changed = True
    content_defaults = defaults.get("content")
    content_contract_version = (
        int(content_defaults.get("contract_version") or 1)
        if isinstance(content_defaults, dict)
        else 1
    )
    if content_contract_version < 2 and content_defaults != DEFAULT_CONTENT:
        defaults["content"] = {
            **DEFAULT_CONTENT,
            "preferred_han_count": list(DEFAULT_CONTENT["preferred_han_count"]),
            "segment_han_targets": dict(DEFAULT_CONTENT["segment_han_targets"]),
            "forbidden_confirmation_openings": list(DEFAULT_CONTENT["forbidden_confirmation_openings"]),
        }
        changed = True
    image_generation = defaults.get("image_generation")
    valid_override = isinstance(image_generation, dict) and (
        (
            image_generation.get("provider") == "codex_imagegen"
            and image_generation.get("selection_mode") == "default"
            and not str(image_generation.get("override_reason") or "").strip()
        )
        or (
            image_generation.get("provider") in {"grok_local", "apimart"}
            and image_generation.get("selection_mode") in {"user_override", "availability_fallback"}
            and bool(str(image_generation.get("override_reason") or "").strip())
        )
    )
    target_image_generation = {
        **DEFAULT_IMAGE_GENERATION,
        "allowed_providers": list(IMAGE_PROVIDERS),
    }
    if valid_override:
        target_image_generation.update(
            {
                "provider": image_generation["provider"],
                "selection_mode": image_generation["selection_mode"],
                "override_reason": image_generation.get("override_reason"),
            }
        )
    if image_generation != target_image_generation:
        defaults["image_generation"] = target_image_generation
        changed = True
    if not isinstance(defaults.get("video_generation"), dict):
        defaults["video_generation"] = DEFAULT_VIDEO_GENERATION.copy()
        changed = True
    if not isinstance(defaults.get("typography"), dict):
        defaults["typography"] = DEFAULT_TYPOGRAPHY.copy()
        changed = True
    if defaults.get("parallel_pipeline") != DEFAULT_PARALLEL_PIPELINE:
        defaults["parallel_pipeline"] = {
            **DEFAULT_PARALLEL_PIPELINE,
            "resource_groups": list(DEFAULT_PARALLEL_PIPELINE["resource_groups"]),
            "progress_reporting": dict(DEFAULT_PARALLEL_PIPELINE["progress_reporting"]),
            "paired_review_steps": list(DEFAULT_PARALLEL_PIPELINE["paired_review_steps"]),
        }
        changed = True
    if defaults.get("delivery") != DEFAULT_DELIVERY:
        defaults["delivery"] = {
            "profile": DEFAULT_DELIVERY["profile"],
            "video_master": dict(DEFAULT_DELIVERY["video_master"]),
            "jianying_draft": dict(DEFAULT_DELIVERY["jianying_draft"]),
        }
        changed = True
    return changed


def merged_status(items: list[dict[str, Any]]) -> str:
    statuses = [str(item.get("status", "pending")) for item in items]
    if all(status == "locked" for status in statuses):
        return "confirmed"
    if all(status == "pending" for status in statuses):
        return "pending"
    if "blocked" in statuses:
        return "blocked"
    if "stale" in statuses:
        return "stale"
    return "working"


def merge_group(old_steps: dict[str, Any], names: list[str]) -> dict[str, Any]:
    items = [old_steps.get(name, {"status": "pending", "version": None, "artifacts": []}) for name in names]
    artifacts: list[str] = []
    versions: list[str] = []
    for item in items:
        for artifact in item.get("artifacts", []):
            if artifact not in artifacts:
                artifacts.append(artifact)
        if item.get("version"):
            versions.append(str(item["version"]))
    return {
        "status": merged_status(items),
        "version": max(versions) if versions else None,
        "artifacts": artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="迁移情绪读书视频项目到五次确认、六个状态节点流程")
    parser.add_argument("--project", required=True, type=Path)
    args = parser.parse_args()

    project = args.project.expanduser().resolve()
    manifest_path = project / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"未找到 manifest.json：{manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = manifest.get("schema_version")
    if schema not in {7, 8}:
        raise SystemExit(f"只支持 schema 7 → 8，当前为：{schema}")
    (project / "08A-片头遮罩素材").mkdir(exist_ok=True)
    if schema == 8:
        steps = manifest.setdefault("steps", {})
        added_final_video = "final_video" not in steps
        if added_final_video:
            legacy_delivery = steps.get("jianying_draft", {})
            final_artifacts = [
                artifact for artifact in legacy_delivery.get("artifacts", [])
                if "final-video-" in str(artifact)
            ]
            steps["final_video"] = {
                "status": legacy_delivery.get("status", "pending") if final_artifacts else "pending",
                "version": legacy_delivery.get("version") if final_artifacts else None,
                "artifacts": final_artifacts,
            }
        defaults_changed = ensure_defaults(manifest)
        if defaults_changed or added_final_video:
            manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        print(manifest_path)
        return 0
    old_steps = manifest.get("steps", {})
    manifest["schema_version"] = 8
    ensure_defaults(manifest)
    manifest["steps"] = {
        gate: merge_group(old_steps, members) for gate, members in GROUPS.items()
    }
    manifest["workflow_migration"] = {
        "from_schema": 7,
        "to_schema": 8,
        "migrated_at_utc": datetime.now(timezone.utc).isoformat(),
        "legacy_step_statuses": {
            name: value.get("status") for name, value in old_steps.items()
        },
    }
    manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

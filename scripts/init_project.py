#!/usr/bin/env python3
"""初始化一个情绪读书视频项目。"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


STEPS = [
    "content_package",
    "sound_package",
    "visual_package",
    "timeline_package",
    "final_video",
    "jianying_draft",
]

DIRECTORIES = [
    "01-书籍资料",
    "02-情绪提炼",
    "03-逐字稿",
    "04-声音设计",
    "05-配音",
    "06-配乐音效",
    "07-分镜",
    "08-正文画面",
    "08A-片头遮罩素材",
    "09-Grok视频",
    "10-片头字幕",
    "11-时间轴",
    "12-预览",
    "13-剪映草稿",
]

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

IMAGE_PROVIDERS = ["codex_imagegen", "grok_local", "apimart"]
DEFAULT_IMAGE_PROVIDER = "codex_imagegen"
DEFAULT_IMAGE_GENERATION_WORKFLOW = {
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
DEFAULT_CONTENT = {
    "contract_version": 3,
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
    "mask_keyword_han_count": 2,
    "mask_preview_required": True,
    "mask_approval_stage": "content_package",
    "mask_background_mode": "fixed_library_video",
    "mask_video_library_manifest": "assets/opening-mask-video-library/manifest.json",
    "mask_default_asset_id": "seagulls-over-sea-close-v001",
    "mask_source_still_allowed": False,
    "mask_image_to_video_allowed": False,
    "book_lead_template": "今天分享的是，《{title}》。",
    "book_title_delivery": {
        "lead_text": "今天分享的是",
        "pre_title_pause_seconds": [0.45, 0.65],
        "pre_title_target_seconds": 0.55,
        "post_title_pause_seconds": [0.45, 0.70],
        "post_title_target_seconds": 0.60,
        "title_emphasis": "firm_low_falling",
        "timing_evidence_required": True,
        "fallback": "pause_only_postprocess",
    },
    "forbidden_confirmation_openings": [
        "你是不是也这样",
        "你有没有发现",
        "你是否也",
        "有没有过这种时候",
        "你是不是经常",
    ],
}
DEFAULT_MUSIC = {
    "selection_mode": "user_provided_library_only",
    "library_manifest": "assets/bgm-library/library.json",
    "required_source_scope": "user_provided_local_file",
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


def safe_name(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "-", value.strip())
    return cleaned.strip("-.") or "未命名书籍"


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化情绪读书视频项目")
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--duration", type=float, help="仅在用户明确指定时长时使用；省略则按完整情绪弧自适应")
    parser.add_argument("--date", help="YYYYMMDD，默认使用 UTC 当天")
    parser.add_argument(
        "--image-provider",
        choices=IMAGE_PROVIDERS,
        default=DEFAULT_IMAGE_PROVIDER,
        help="正文生图提供方；默认 Codex App image_gen，可显式切换 Grok 或 APIMart",
    )
    args = parser.parse_args()

    if args.duration is not None and args.duration <= 0:
        parser.error("显式 --duration 必须大于 0")
    if args.duration is not None and args.duration > DEFAULT_CONTENT["max_script_seconds"]:
        parser.error("市场发布规则要求成片不得超过 60 秒")

    content_policy = {**DEFAULT_CONTENT}

    now = datetime.now(timezone.utc)
    date_text = args.date or now.strftime("%Y%m%d")
    if not re.fullmatch(r"\d{8}", date_text):
        parser.error("--date 必须是 YYYYMMDD")

    project = args.output_root.resolve() / f"{safe_name(args.title)}_{date_text}_情绪读书视频"
    if project.exists():
        raise SystemExit(f"项目已存在，不覆盖：{project}")

    project.mkdir(parents=True)
    for directory in DIRECTORIES:
        (project / directory).mkdir()

    manifest = {
        "schema_version": 8,
        "title": args.title.strip(),
        "author": args.author.strip(),
        "created_at_utc": now.isoformat(),
        "updated_at_utc": now.isoformat(),
        "canvas": {"width": 1080, "height": 1440, "fps": 30},
        "defaults": {
            "voice": DEFAULT_VOICE,
            "image_generation": {
                "provider": args.image_provider,
                "selection_mode": "default" if args.image_provider == DEFAULT_IMAGE_PROVIDER else "user_override",
                "override_reason": None if args.image_provider == DEFAULT_IMAGE_PROVIDER else "用户在初始化时显式指定",
                "fallback_provider": "grok_local",
                "allowed_providers": IMAGE_PROVIDERS,
                **DEFAULT_IMAGE_GENERATION_WORKFLOW,
            },
            "video_generation": DEFAULT_VIDEO_GENERATION,
            "typography": DEFAULT_TYPOGRAPHY,
            "content": content_policy,
            "music": DEFAULT_MUSIC,
            "parallel_pipeline": DEFAULT_PARALLEL_PIPELINE,
            "delivery": DEFAULT_DELIVERY,
        },
        "duration": {
            "mode": "fixed" if args.duration is not None else "adaptive",
            "requested": args.duration,
            "observed_reference_range_seconds": [42, 66],
            "estimated": None,
            "locked": None,
        },
        "steps": {step: {"status": "pending", "version": None, "artifacts": []} for step in STEPS},
    }
    (project / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

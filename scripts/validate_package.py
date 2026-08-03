#!/usr/bin/env python3
"""检查情绪读书视频项目的文案、时间轴和可选成片。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image


DEFAULT_VOICE_SPEAKER = "S_Bkoh3uBT1"
REFERENCE_SPEED_VIDEO_ID = "7668678283642779072"
FIXED_PROVIDER_SPEECH_RATE = 10
FIXED_VOICE_CPS = 4.56
FIXED_VOICE_CPS_TOLERANCE = 0.02
DEFAULT_TARGET_SCRIPT_HAN = 256
DEFAULT_MAX_SCRIPT_HAN = 270
DEFAULT_PREFERRED_SCRIPT_HAN = [245, 268]
DEFAULT_SEGMENT_HAN_TARGETS = {
    "hook": 14,
    "book_lead": 12,
    "viewer_expression": 46,
    "pressure_escalation": 54,
    "cognitive_reversal": 62,
    "action_permission": 36,
    "identity_close": 32,
}
DEFAULT_IMAGE_PROVIDER = "codex_imagegen"
ALLOWED_IMAGE_PROVIDERS = {"codex_imagegen", "grok_local", "apimart"}
DEFAULT_IMAGE_GENERATION_MODE = "parallel_individual"
DEFAULT_IMAGE_BATCH_STRATEGY = "parallel_all"
DEFAULT_VIDEO_PROVIDER = "grok_cli"
DEFAULT_CHINESE_FONT_ID = "yrdzst-heavy"
DEFAULT_CHINESE_FONT_ASSET = "assets/fonts/杨任东竹石体-Heavy.ttf"
DEFAULT_CHINESE_FONT_SHA256 = "61996afd2b52e92e1228b724dd6cc90c91b732eae79aa16dc2fa8f4ef9e0b70a"
DEFAULT_MAX_SCRIPT_SECONDS = 60.0
BOOK_LEAD_TEXT = "今天分享的是"
BOOK_TITLE_PRE_PAUSE_RANGE = [0.45, 0.65]
BOOK_TITLE_PRE_PAUSE_TARGET = 0.55
BOOK_TITLE_POST_PAUSE_RANGE = [0.45, 0.70]
BOOK_TITLE_POST_PAUSE_TARGET = 0.60
BOOK_TITLE_EMPHASIS = "firm_low_falling"
DEFAULT_CAROUSEL_TIMING = {
    "mode": "voice_timing_derived",
    "fps": 30,
    "carousel_start_seconds": 2.90,
    "target_cover_lead_frames": 0,
    "card_frame_range": [3, 4],
    "minimum_cards": 6,
    "estimate_formula": "(hook_han + lead_text_han) / chars_per_second + pre_title_pause",
    "final_timing_source": "voice_actual",
    "final_replan_required": True,
    "insufficient_library_policy": "block_expand_library",
}
TIMING_TOLERANCE_SECONDS = 0.05
ALLOWED_BODY_SHOT_SIZES = {"medium_long", "long"}
ALLOWED_WARDROBES = {"light_knit", "shirt", "short_jacket", "light_top", "simple_dress"}
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
LEGACY_PARALLEL_PIPELINE = {
    "mode": "parallel_after_content_lock",
    "content_lock_required": True,
    "lanes": ["voice", "body_visual", "opening", "subtitle_music"],
    "dispatch_policy": "start_all_lanes_without_waiting",
    "image_to_video_trigger": "per_image_qc_pass",
    "pre_join_timing_basis": "script_estimated",
    "final_timing_basis": "voice_actual",
    "join_policy": "wait_all_lanes_then_bind_actual_timing",
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
FORBIDDEN_CONFIRMATION_OPENINGS = {
    "你是不是也这样",
    "你有没有发现",
    "你是否也",
    "有没有过这种时候",
    "你是不是经常",
}


def newest(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern))
    return matches[-1] if matches else None


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def resolve_project_asset(project: Path, value: Any) -> Path:
    path = Path(str(value or "")).expanduser()
    return path.resolve() if path.is_absolute() else (project / path).resolve()


def same_grayscale_pixels(left: Path, right: Path) -> bool:
    if not left.is_file() or not right.is_file():
        return False
    try:
        with Image.open(left) as left_image, Image.open(right) as right_image:
            left_gray = left_image.convert("L")
            right_gray = right_image.convert("L")
            return left_gray.size == right_gray.size and left_gray.tobytes() == right_gray.tobytes()
    except OSError:
        return False


def content_is_distinct(asset: Path, candidates: list[Path]) -> bool:
    if not asset.is_file():
        return False
    asset_hash = sha256(asset)
    return all(not candidate.is_file() or sha256(candidate) != asset_hash for candidate in candidates)


def han_count(text: str) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", text or ""))


def add(checks: list[dict[str, Any]], name: str, ok: bool, detail: str) -> None:
    checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})


def finish(checks: list[dict[str, Any]], stage: str) -> int:
    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    print(json.dumps({"status": status, "stage": stage, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


def find_secret_fields(value: Any, path: str = "$") -> list[str]:
    """返回不应落盘的凭证字段路径。"""
    forbidden = {
        "access_token",
        "refresh_token",
        "id_token",
        "authorization",
        "api_key",
        "client_secret",
    }
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() in forbidden and child is not None and child is not False and child != "":
                found.append(child_path)
            found.extend(find_secret_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_secret_fields(child, f"{path}[{index}]"))
    return found


def ffprobe(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type,codec_name,pix_fmt,width,height,avg_frame_rate,sample_rate,channels",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def frame_rate(value: Any) -> float | None:
    text = str(value or "")
    try:
        if "/" in text:
            numerator, denominator = text.split("/", 1)
            denominator_value = float(denominator)
            return float(numerator) / denominator_value if denominator_value else None
        return float(text)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def loudness(path: Path) -> dict[str, float]:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        "loudnorm=I=-10:LRA=3:TP=-1:print_format=json",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    start = result.stderr.rfind("{")
    end = result.stderr.rfind("}")
    if start < 0 or end < start:
        raise ValueError("ffmpeg 未返回 loudnorm JSON")
    data = json.loads(result.stderr[start : end + 1])
    return {
        "lufs": float(data["input_i"]),
        "lra": float(data["input_lra"]),
        "true_peak": float(data["input_tp"]),
    }


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def in_range(value: Any, low: float, high: float) -> bool:
    number = as_float(value)
    return number is not None and low <= number <= high


def parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def validate_parallel_pipeline_run(
    run: Any,
    project: Path,
    script_path: Path | None,
    expected_shot_ids: set[str],
) -> list[str]:
    """校验内容锁后的事件驱动 DAG、逐素材推进和实际时码汇合证据。"""
    errors: list[str] = []
    if not isinstance(run, dict):
        return ["pipeline_run:missing"]
    if run.get("mode") == "parallel_after_content_lock":
        if run.get("dispatch_policy") != "start_all_lanes_without_waiting":
            errors.append("legacy_pipeline_run:dispatch_policy")
        script_lock_value = str(run.get("script_lock") or "")
        script_lock_path = project / script_lock_value
        if not script_lock_value or not is_within(script_lock_path, project) or not script_lock_path.is_file():
            errors.append("legacy_pipeline_run:script_lock")
        elif script_path is None or not script_path.is_file():
            errors.append("legacy_pipeline_run:script_source")
        else:
            lock = read_json(script_lock_path)
            if (
                str(lock.get("script") or "") != str(script_path.relative_to(project))
                or str(lock.get("script_sha256") or "") != sha256(script_path)
                or lock.get("timing_basis") != "script_estimated"
                or parse_timestamp(lock.get("locked_at_utc")) is None
            ):
                errors.append("legacy_pipeline_run:script_lock_content")
        lanes = run.get("lanes")
        required_lanes = set(LEGACY_PARALLEL_PIPELINE["lanes"])
        lane_times: list[tuple[datetime, datetime]] = []
        if not isinstance(lanes, dict) or set(lanes) != required_lanes:
            errors.append("legacy_pipeline_run:lanes")
        else:
            for lane_id, lane in lanes.items():
                started = parse_timestamp(lane.get("started_at_utc")) if isinstance(lane, dict) else None
                completed = parse_timestamp(lane.get("completed_at_utc")) if isinstance(lane, dict) else None
                if (
                    not isinstance(lane, dict)
                    or lane.get("status") != "ready_for_join"
                    or started is None
                    or completed is None
                    or completed < started
                ):
                    errors.append(f"legacy_pipeline_lane:{lane_id}")
                    continue
                lane_times.append((started, completed))
        if len(lane_times) >= 2 and not any(
            max(left[0], right[0]) < min(left[1], right[1])
            for index, left in enumerate(lane_times)
            for right in lane_times[index + 1 :]
        ):
            errors.append("legacy_pipeline_run:no_overlap")
        events = run.get("image_events")
        observed_shots: set[str] = set()
        if not isinstance(events, list):
            errors.append("legacy_pipeline_run:image_events")
        else:
            for event in events:
                if not isinstance(event, dict):
                    errors.append("legacy_pipeline_event:object")
                    continue
                shot_id = str(event.get("shot_id") or "")
                stamps = [
                    parse_timestamp(event.get(key))
                    for key in (
                        "image_completed_at_utc",
                        "qc_passed_at_utc",
                        "video_started_at_utc",
                        "video_raw_completed_at_utc",
                    )
                ]
                if not shot_id or any(item is None for item in stamps):
                    errors.append(f"legacy_pipeline_event:{shot_id or 'unknown'}")
                    continue
                observed_shots.add(shot_id)
                concrete_stamps = [item for item in stamps if item is not None]
                if concrete_stamps != sorted(concrete_stamps):
                    errors.append(f"legacy_pipeline_event:{shot_id}:order")
        if observed_shots != expected_shot_ids:
            errors.append("legacy_pipeline_run:event_shots_mismatch")
        join = run.get("join")
        if not isinstance(join, dict) or join.get("status") != "completed":
            errors.append("legacy_pipeline_run:join")
        else:
            timing_source = project / str(join.get("actual_timing_source") or "")
            timing_binding = project / str(join.get("timing_binding") or "")
            joined_at = parse_timestamp(join.get("joined_at_utc"))
            if not timing_source.is_file() or not timing_binding.is_file() or joined_at is None:
                errors.append("legacy_pipeline_run:join_artifacts")
            elif lane_times and joined_at < max(item[1] for item in lane_times):
                errors.append("legacy_pipeline_run:join_before_lanes")
        return errors
    if run.get("mode") != "event_driven_dag_after_content_lock":
        errors.append("pipeline_run:mode")
    if run.get("scheduler") != "dependency_ready_queue":
        errors.append("pipeline_run:scheduler")
    if run.get("dispatch_policy") != "dispatch_when_dependencies_completed":
        errors.append("pipeline_run:dispatch_policy")
    if run.get("progression_policy") != "advance_each_asset_immediately":
        errors.append("pipeline_run:progression_policy")
    if run.get("failure_scope") != "descendants_only":
        errors.append("pipeline_run:failure_scope")
    script_lock_value = str(run.get("script_lock") or "")
    script_lock_path = project / script_lock_value
    script_locked_at: datetime | None = None
    if not script_lock_value or not is_within(script_lock_path, project) or not script_lock_path.is_file():
        errors.append("pipeline_run:script_lock")
    elif script_path is None or not script_path.is_file():
        errors.append("pipeline_run:script_source")
    else:
        lock = read_json(script_lock_path)
        script_locked_at = parse_timestamp(lock.get("locked_at_utc"))
        if (
            str(lock.get("script") or "") != str(script_path.relative_to(project))
            or str(lock.get("script_sha256") or "") != sha256(script_path)
            or lock.get("timing_basis") != "script_estimated"
            or script_locked_at is None
        ):
            errors.append("pipeline_run:script_lock_content")

    tasks = run.get("tasks")
    task_map: dict[str, dict[str, Any]] = {}
    task_times: dict[str, tuple[datetime, datetime]] = {}
    if not isinstance(tasks, list) or not tasks:
        errors.append("pipeline_run:tasks")
    else:
        for index, task in enumerate(tasks, start=1):
            if not isinstance(task, dict):
                errors.append(f"pipeline_task#{index}:object")
                continue
            task_id = str(task.get("id") or "").strip()
            started = parse_timestamp(task.get("started_at_utc"))
            completed = parse_timestamp(task.get("completed_at_utc"))
            dependencies = task.get("depends_on")
            if not task_id or task_id in task_map:
                errors.append(f"pipeline_task#{index}:id")
                continue
            task_map[task_id] = task
            if (
                task.get("status") not in {"completed", "fallback"}
                or started is None
                or completed is None
                or completed < started
                or not isinstance(dependencies, list)
            ):
                errors.append(f"pipeline_task:{task_id}:contract")
                continue
            task_times[task_id] = (started, completed)

        max_delay = float(DEFAULT_PARALLEL_PIPELINE["max_ready_queue_delay_seconds"])
        for task_id, task in task_map.items():
            dependencies = task.get("depends_on")
            if not isinstance(dependencies, list) or task_id not in task_times:
                continue
            dependency_ids = [str(item) for item in dependencies]
            if any(item not in task_map for item in dependency_ids):
                errors.append(f"pipeline_task:{task_id}:unknown_dependency")
                continue
            if any(item not in task_times for item in dependency_ids):
                continue
            if task_id in dependency_ids:
                errors.append(f"pipeline_task:{task_id}:self_dependency")
                continue
            if dependency_ids:
                ready_at = max(task_times[item][1] for item in dependency_ids)
                started_at = task_times[task_id][0]
                delay = (started_at - ready_at).total_seconds()
                if delay < 0:
                    errors.append(f"pipeline_task:{task_id}:started_before_ready")
                elif delay > max_delay:
                    errors.append(f"pipeline_task:{task_id}:ready_queue_delay")
            elif script_locked_at is not None:
                root_delay = (task_times[task_id][0] - script_locked_at).total_seconds()
                if root_delay < 0:
                    errors.append(f"pipeline_task:{task_id}:started_before_script_lock")
                elif root_delay > max_delay:
                    errors.append(f"pipeline_task:{task_id}:root_queue_delay")

    expected_task_suffixes = {"image", "image_qc", "video_raw", "video_final"}
    observed_shots: set[str] = set()
    for shot_id in expected_shot_ids:
        required_ids = {f"{shot_id}.{suffix}" for suffix in expected_task_suffixes}
        if not required_ids.issubset(task_map):
            errors.append(f"pipeline_shot:{shot_id}:missing_tasks")
            continue
        observed_shots.add(shot_id)
        if task_map[f"{shot_id}.image_qc"].get("depends_on") != [f"{shot_id}.image"]:
            errors.append(f"pipeline_shot:{shot_id}:image_qc_dependency")
        if task_map[f"{shot_id}.video_raw"].get("depends_on") != [f"{shot_id}.image_qc"]:
            errors.append(f"pipeline_shot:{shot_id}:video_raw_dependency")
        final_dependencies = set(task_map[f"{shot_id}.video_final"].get("depends_on") or [])
        if final_dependencies != {f"{shot_id}.video_raw", "timing.bind"}:
            errors.append(f"pipeline_shot:{shot_id}:video_final_dependency")
    if expected_shot_ids and observed_shots != expected_shot_ids:
        errors.append("pipeline_run:event_shots_mismatch")

    intervals = list(task_times.items())
    independent_overlap = False
    for index, (left_id, (left_start, left_end)) in enumerate(intervals):
        left_deps = set(task_map[left_id].get("depends_on") or [])
        for right_id, (right_start, right_end) in intervals[index + 1:]:
            right_deps = set(task_map[right_id].get("depends_on") or [])
            directly_related = right_id in left_deps or left_id in right_deps
            if not directly_related and max(left_start, right_start) < min(left_end, right_end):
                independent_overlap = True
                break
        if independent_overlap:
            break
    if not independent_overlap:
        errors.append("pipeline_run:no_independent_overlap")

    timing_bind = task_map.get("timing.bind")
    if not isinstance(timing_bind, dict) or "voice.generate" not in set(timing_bind.get("depends_on") or []):
        errors.append("pipeline_run:timing_bind_dependency")

    join = run.get("join")
    if not isinstance(join, dict) or join.get("status") != "completed":
        errors.append("pipeline_run:join")
    else:
        timing_source = project / str(join.get("actual_timing_source") or "")
        timing_binding = project / str(join.get("timing_binding") or "")
        joined_at = parse_timestamp(join.get("joined_at_utc"))
        if not timing_source.is_file() or not timing_binding.is_file() or joined_at is None:
            errors.append("pipeline_run:join_artifacts")
        elif task_times and joined_at < max(item[1] for item in task_times.values()):
            errors.append("pipeline_run:join_before_tasks")

    progress = run.get("progress")
    if not isinstance(progress, dict) or progress.get("heartbeat_seconds") != 60:
        errors.append("pipeline_run:progress_contract")
    else:
        progress_json = project / str(progress.get("json") or "")
        progress_markdown = project / str(progress.get("markdown") or "")
        if (
            not is_within(progress_json, project)
            or not progress_json.is_file()
            or not is_within(progress_markdown, project)
            or not progress_markdown.is_file()
        ):
            errors.append("pipeline_run:progress_files")
        else:
            snapshot = read_json(progress_json)
            overall = snapshot.get("overall") if isinstance(snapshot, dict) else None
            terminal_count = sum(
                1 for item in task_map.values()
                if item.get("status") in {"completed", "fallback"}
            )
            updated_at = parse_timestamp(snapshot.get("updated_at_utc"))
            snapshot_ok = (
                isinstance(overall, dict)
                and overall.get("total") == len(task_map)
                and overall.get("finished") == terminal_count
                and isinstance(snapshot.get("resource_groups"), dict)
                and isinstance(snapshot.get("shots"), dict)
                and updated_at is not None
            )
            if task_times and updated_at is not None:
                snapshot_ok = snapshot_ok and updated_at >= max(item[1] for item in task_times.values())
            if not snapshot_ok:
                errors.append("pipeline_run:progress_snapshot")
    return errors


def normalized_book_title(value: Any) -> str:
    return str(value or "").strip().removeprefix("《").removesuffix("》").strip()


def valid_voice_policy(voice: dict[str, Any]) -> bool:
    selection_mode = voice.get("selection_mode")
    speaker = str(voice.get("speaker") or "").strip()
    override_reason = str(voice.get("override_reason") or "").strip()
    return (
        selection_mode == "default" and speaker == DEFAULT_VOICE_SPEAKER
    ) or (
        selection_mode in {"user_override", "availability_fallback"}
        and bool(speaker)
        and bool(override_reason)
    )


def valid_voice_selection_policy(selection: dict[str, Any], blueprint_mode: Any) -> bool:
    selection_mode = selection.get("selection_mode")
    return selection_mode == blueprint_mode and (
        selection_mode == "default"
        or bool(str(selection.get("override_reason") or "").strip())
    )


def valid_image_policy(image_generation: dict[str, Any]) -> bool:
    provider = image_generation.get("provider")
    selection_mode = image_generation.get("selection_mode")
    override_reason = str(image_generation.get("override_reason") or "").strip()
    provider_policy_ok = (
        provider == DEFAULT_IMAGE_PROVIDER
        and selection_mode == "default"
        and not override_reason
    ) or (
        provider in ALLOWED_IMAGE_PROVIDERS
        and provider != DEFAULT_IMAGE_PROVIDER
        and selection_mode in {"user_override", "availability_fallback"}
        and bool(override_reason)
    )
    return (
        provider_policy_ok
        and set(image_generation.get("allowed_providers", [])) == ALLOWED_IMAGE_PROVIDERS
        and image_generation.get("generation_mode") == DEFAULT_IMAGE_GENERATION_MODE
        and image_generation.get("batch_strategy") == DEFAULT_IMAGE_BATCH_STRATEGY
        and image_generation.get("wait_policy") == "wait_after_all_submitted"
        and image_generation.get("preferred_image_size") == [1536, 2048]
        and image_generation.get("minimum_image_size") == [1080, 1440]
        and image_generation.get("retry_mode") == "parallel_failed_only"
        and image_generation.get("max_retry_batches") == 1
        and image_generation.get("serial_waits_allowed") == 0
    )


def validate_parallel_image_batch(
    plan: Any,
    project: Path,
    expected_provider: str,
    expected_body_outputs: set[str],
) -> list[str]:
    """校验全部主生图请求先提交、再统一等待的批次记录。"""
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["batch_plan:missing"]
    if not str(plan.get("id") or "").strip():
        errors.append("batch_plan:id")
    if plan.get("strategy") != "parallel_all":
        errors.append("batch_plan:strategy")
    if plan.get("serial_wait_count") != 0:
        errors.append("batch_plan:serial_wait_count")
    if plan.get("wait_policy") != "wait_after_all_submitted":
        errors.append("batch_plan:wait_policy")
    if plan.get("result_policy") != "qc_and_trigger_video_per_image":
        errors.append("batch_plan:result_policy")
    all_images_completed = parse_timestamp(plan.get("all_images_completed_at_utc"))
    if all_images_completed is None:
        errors.append("batch_plan:all_images_completed_at_utc")
    requests = plan.get("requests")
    if not isinstance(requests, list) or not requests:
        return errors + ["batch_plan:requests"]
    seen: set[str] = set()
    body_outputs: set[str] = set()
    opening_mask_count = 0
    for index, request in enumerate(requests, start=1):
        label = f"batch_request#{index}"
        if not isinstance(request, dict):
            errors.append(f"{label}:not_object")
            continue
        request_id = str(request.get("id") or "").strip()
        role = request.get("role")
        output = str(request.get("output") or "").strip()
        if not request_id or request_id in seen:
            errors.append(f"{label}:id")
        seen.add(request_id)
        if role == "body_shot":
            body_outputs.add(output)
        elif role == "opening_mask":
            opening_mask_count += 1
        else:
            errors.append(f"{label}:role")
        if request.get("provider") != expected_provider:
            errors.append(f"{label}:provider")
        if request.get("status") != "completed":
            errors.append(f"{label}:status")
        if role == "body_shot":
            image_completed = parse_timestamp(request.get("image_completed_at_utc"))
            qc_passed = parse_timestamp(request.get("qc_passed_at_utc"))
            video_started = parse_timestamp(request.get("video_started_at_utc"))
            if (
                None in {image_completed, qc_passed, video_started}
                or not (image_completed <= qc_passed <= video_started)
            ):
                errors.append(f"{label}:event_timing")
        request_output = project / output
        if not output or not is_within(request_output, project) or not request_output.is_file():
            errors.append(f"{label}:output")
    if body_outputs != expected_body_outputs:
        errors.append("batch_plan:body_outputs_mismatch")
    if opening_mask_count != 1:
        errors.append("batch_plan:opening_mask_count")
    retry = plan.get("retry_batch")
    if retry is not None:
        if not isinstance(retry, dict):
            errors.append("retry_batch:not_object")
        else:
            if retry.get("mode") != "parallel_failed_only":
                errors.append("retry_batch:mode")
            if retry.get("serial_wait_count") != 0:
                errors.append("retry_batch:serial_wait_count")
            if retry.get("wait_policy") != "wait_after_all_submitted":
                errors.append("retry_batch:wait_policy")
            retry_requests = retry.get("requests", [])
            if not isinstance(retry_requests, list):
                errors.append("retry_batch:requests")
            else:
                if retry_requests and not str(retry.get("id") or "").strip():
                    errors.append("retry_batch:id")
                for index, request in enumerate(retry_requests, start=1):
                    if not isinstance(request, dict):
                        errors.append(f"retry_request#{index}:not_object")
                        continue
                    if request.get("role") != "image_retry":
                        errors.append(f"retry_request#{index}:role")
                    if request.get("status") != "completed":
                        errors.append(f"retry_request#{index}:status")
                    output = str(request.get("output") or "")
                    request_output = project / output
                    if not output or not is_within(request_output, project) or not request_output.is_file():
                        errors.append(f"retry_request#{index}:output")
    return errors


def validate_image_shot_contract(
    shots: Any,
    outputs: Any,
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """校验逐字稿到侧脸风景图的机器绑定，并按输出路径建立索引。"""
    errors: list[str] = []
    by_output: dict[str, dict[str, Any]] = {}
    if not isinstance(shots, list) or not shots:
        return ["shots:missing"], by_output
    output_set = {str(item) for item in outputs} if isinstance(outputs, list) else set()
    seen_ids: set[str] = set()
    for index, shot in enumerate(shots, start=1):
        label = f"shot#{index}"
        if not isinstance(shot, dict):
            errors.append(f"{label}:not_object")
            continue
        shot_id = str(shot.get("id") or "").strip()
        output = str(shot.get("output") or "").strip()
        segment_ids = shot.get("script_segment_ids")
        voice_start = as_float(shot.get("voice_start"))
        voice_end = as_float(shot.get("voice_end"))
        estimated_voice_start = as_float(shot.get("estimated_voice_start"))
        estimated_voice_end = as_float(shot.get("estimated_voice_end"))
        composition = shot.get("composition")
        if not shot_id or shot_id in seen_ids:
            errors.append(f"{label}:id")
        seen_ids.add(shot_id)
        if not output or output in by_output:
            errors.append(f"{label}:output")
        if output:
            by_output[output] = shot
        if not isinstance(segment_ids, list) or not segment_ids or not all(str(item).strip() for item in segment_ids):
            errors.append(f"{label}:script_segment_ids")
        if not str(shot.get("narration_text") or "").strip():
            errors.append(f"{label}:narration_text")
        if voice_start is None or voice_end is None or voice_start < 0 or voice_end <= voice_start:
            errors.append(f"{label}:voice_range")
        if estimated_voice_start is None or estimated_voice_end is None or estimated_voice_start < 0 or estimated_voice_end <= estimated_voice_start:
            errors.append(f"{label}:estimated_voice_range")
        if not str(shot.get("emotional_stage") or "").strip():
            errors.append(f"{label}:emotional_stage")
        if len(str(shot.get("character_emotion") or "").strip()) < 4:
            errors.append(f"{label}:character_emotion")
        if len(str(shot.get("environment_emotional_function") or "").strip()) < 6:
            errors.append(f"{label}:environment_emotional_function")
        if len(str(shot.get("emotion_environment_alignment_reason") or "").strip()) < 8:
            errors.append(f"{label}:emotion_environment_alignment_reason")
        if not str(shot.get("image_prompt") or "").strip():
            errors.append(f"{label}:image_prompt")
        source_type = shot.get("source_type")
        if source_type == "direct_generation":
            if not str(shot.get("batch_id") or "").strip():
                errors.append(f"{label}:batch_id")
            if not str(shot.get("request_id") or "").strip():
                errors.append(f"{label}:request_id")
        elif source_type == "retry_generation":
            if not str(shot.get("retry_batch_id") or "").strip():
                errors.append(f"{label}:retry_batch_id")
        else:
            errors.append(f"{label}:source_type")
        if not isinstance(composition, dict):
            errors.append(f"{label}:composition")
            continue
        landscape_elements = composition.get("landscape_elements")
        composition_ok = (
            composition.get("human_required") is True
            and composition.get("face_orientation") == "side_profile"
            and composition.get("shot_size") in ALLOWED_BODY_SHOT_SIZES
            and composition.get("character_gender") == "young_woman"
            and composition.get("wardrobe") in ALLOWED_WARDROBES
            and composition.get("long_coat") is False
            and composition.get("landscape_required") is True
            and isinstance(landscape_elements, list)
            and bool(landscape_elements)
            and all(str(item).strip() for item in landscape_elements)
            and composition.get("clarity") == "clear_transparent"
            and composition.get("atmospheric_haze") == "none"
            and composition.get("white_veil") is False
            and composition.get("contrast") == "clean_mid_contrast"
            and composition.get("highlights_controlled") is True
            and composition.get("text_free") is True
            and composition.get("subtitle_safe_area") is True
        )
        if not composition_ok:
            errors.append(f"{label}:side_profile_clear_wardrobe_landscape")
    if set(by_output) != output_set:
        errors.append("shots:outputs_mismatch")
    return errors, by_output


def validate_scene_voice_coverage(
    scenes: Any,
    body_voice_start: Any,
    duration_locked: Any,
) -> list[str]:
    """校验正文口播责任区间无缝覆盖片头后至锁定总时长。"""
    errors: list[str] = []
    body_start = as_float(body_voice_start)
    locked = as_float(duration_locked)
    if not isinstance(scenes, list) or not scenes or body_start is None or locked is None:
        return ["coverage:missing"]
    ordered = sorted(scenes, key=lambda item: as_float(item.get("voice_start")) or -1)
    previous_voice_end: float | None = None
    previous_scene_end: float | None = None
    for index, scene in enumerate(ordered, start=1):
        label = str(scene.get("id") or f"scene#{index}")
        start = as_float(scene.get("start"))
        end = as_float(scene.get("end"))
        voice_start = as_float(scene.get("voice_start"))
        voice_end = as_float(scene.get("voice_end"))
        if None in {start, end, voice_start, voice_end}:
            errors.append(f"{label}:missing_time")
            continue
        assert start is not None and end is not None and voice_start is not None and voice_end is not None
        if not (start <= voice_start + TIMING_TOLERANCE_SECONDS and voice_start < voice_end and voice_end <= end + TIMING_TOLERANCE_SECONDS):
            errors.append(f"{label}:scene_does_not_cover_voice")
        if previous_voice_end is not None and abs(voice_start - previous_voice_end) > TIMING_TOLERANCE_SECONDS:
            errors.append(f"{label}:voice_gap_or_overlap")
        if previous_scene_end is not None:
            overlap = previous_scene_end - start
            if overlap < -TIMING_TOLERANCE_SECONDS or overlap > 0.55:
                errors.append(f"{label}:scene_transition_range")
        previous_voice_end = voice_end
        previous_scene_end = end
    first_voice_start = as_float(ordered[0].get("voice_start"))
    last_voice_end = as_float(ordered[-1].get("voice_end"))
    if first_voice_start is None or abs(first_voice_start - body_start) > TIMING_TOLERANCE_SECONDS:
        errors.append("coverage:first_voice_start")
    if last_voice_end is None or abs(last_voice_end - locked) > TIMING_TOLERANCE_SECONDS:
        errors.append("coverage:last_voice_end")
    return errors


def validate_opening_contract(
    opening: dict[str, Any],
    project: Path,
    checks: list[dict[str, Any]],
    target_title: str,
    content_contract_version: int = 1,
) -> None:
    template = opening.get("template")
    add(checks, "opening_template", template == "masked_book_carousel", str(template))
    add(checks, "target_flash_start", in_range(opening.get("target_flash_start"), 0.0, 0.02), str(opening.get("target_flash_start")))
    add(checks, "target_flash_end", in_range(opening.get("target_flash_end"), 0.09, 0.11), str(opening.get("target_flash_end")))
    add(checks, "hook_start", in_range(opening.get("hook_start"), 0.09, 0.11), str(opening.get("hook_start")))
    add(checks, "keyword_hold_end", in_range(opening.get("keyword_hold_end"), 1.30, 1.45), str(opening.get("keyword_hold_end")))
    add(checks, "mask_mode", opening.get("mask_mode") == "horizontal_band_expand", str(opening.get("mask_mode")))
    add(checks, "same_source_video", opening.get("same_source_video") is True, str(opening.get("same_source_video")))
    add(checks, "mask_source_role", opening.get("mask_source_role") == "opening_mask_only", str(opening.get("mask_source_role")))
    add(checks, "body_asset_reuse", opening.get("body_asset_reuse") is False, str(opening.get("body_asset_reuse")))
    add(
        checks,
        "opening_mask_content_reviewed",
        opening.get("content_independence_reviewed") is True,
        str(opening.get("content_independence_reviewed")),
    )
    add(checks, "keyword_mask_style", opening.get("keyword_mask_style") == "custom_reviewed", str(opening.get("keyword_mask_style")))
    if content_contract_version >= 3:
        opening_delivery = opening.get("book_title_delivery", {})
        opening_pre_pause = as_float(opening_delivery.get("pre_title_pause_seconds"))
        opening_post_pause = as_float(opening_delivery.get("post_title_pause_seconds"))
        opening_delivery_ok = (
            opening_delivery.get("lead_text") == BOOK_LEAD_TEXT
            and str(opening_delivery.get("title_text") or "").strip().strip("《》") == str(target_title or "").strip().strip("《》")
            and opening_pre_pause is not None
            and BOOK_TITLE_PRE_PAUSE_RANGE[0] <= opening_pre_pause <= BOOK_TITLE_PRE_PAUSE_RANGE[1]
            and opening_post_pause is not None
            and BOOK_TITLE_POST_PAUSE_RANGE[0] <= opening_post_pause <= BOOK_TITLE_POST_PAUSE_RANGE[1]
            and opening_delivery.get("title_emphasis") == BOOK_TITLE_EMPHASIS
            and bool(str(opening_delivery.get("timing_source") or "").startswith("05-配音/timing-v"))
        )
        add(checks, "opening_book_title_delivery", opening_delivery_ok, str(opening_delivery))
    content_mask_record_path = newest(project / "02-情绪提炼", "mask-keyword-v*.json")
    if content_mask_record_path:
        content_mask_record = read_json(content_mask_record_path)
        approved_keyword = str(content_mask_record.get("keyword") or "")
        opening_keyword = str(opening.get("keyword") or "")
        exact_two_reused = (
            bool(re.fullmatch(r"[\u3400-\u9fff]{2}", approved_keyword))
            and opening_keyword == approved_keyword
            and content_mask_record.get("review_status") == "confirmed"
        )
        add(checks, "opening_keyword_exact_two", exact_two_reused, f"内容包 {approved_keyword} / 片头 {opening_keyword}")
        approved_alpha = resolve_project_asset(project, content_mask_record.get("alpha_mask"))
        rendered_keyword_mask = project / str(opening.get("keyword_mask_asset", ""))
        add(
            checks,
            "opening_reuses_confirmed_content_mask",
            same_grayscale_pixels(approved_alpha, rendered_keyword_mask),
            f"{approved_alpha} → {rendered_keyword_mask}",
        )
    for name in ("mask_source_video_asset", "mask_source_plan_asset", "keyword_mask_asset", "masked_keyword_video_asset"):
        asset_value = str(opening.get(name, ""))
        add(checks, name, bool(asset_value) and (project / asset_value).is_file(), asset_value or "缺失")
    mask_root = project / "08A-片头遮罩素材"
    mask_image_value = str(opening.get("mask_source_image_asset", ""))
    mask_image = project / mask_image_value if mask_image_value else None
    mask_video = project / str(opening.get("mask_source_video_asset", ""))
    mask_plan = project / str(opening.get("mask_source_plan_asset", ""))
    image_suffixes = {".png", ".jpg", ".jpeg", ".webp"}
    video_suffixes = {".mp4", ".mov", ".m4v", ".webm"}
    mask_paths_ok = (
        is_within(mask_video, mask_root)
        and is_within(mask_plan, mask_root)
        and (mask_image is None or (is_within(mask_image, mask_root) and mask_image.suffix.lower() in image_suffixes))
        and mask_video.suffix.lower() in video_suffixes
        and mask_plan.suffix.lower() == ".json"
    )
    add(checks, "opening_mask_dedicated_paths", mask_paths_ok, f"{mask_image} / {mask_video}")
    mask_plan_ok = False
    if mask_plan.is_file():
        plan = read_json(mask_plan)
        library_plan = plan.get("library_video", {})
        mask_plan_ok = (
            plan.get("role") == "opening_mask_only"
            and plan.get("content_independence_reviewed") is True
            and library_plan.get("provider") == "local_asset_library"
            and library_plan.get("mode") == "approved_library_video"
            and library_plan.get("asset_id") == "seagulls-over-sea-close-v001"
            and library_plan.get("output") == str(opening.get("mask_source_video_asset", ""))
            and library_plan.get("status") == "approved"
            and library_plan.get("sha256") == "4c83260585277afe6fcdbd1c6b1e4af837a645ad7e6fdd635ab07eb7672ea46a"
            and not find_secret_fields(plan)
        )
    add(checks, "opening_mask_plan", mask_plan_ok, str(mask_plan))
    mask_captions = opening.get("mask_caption_track", [])
    mask_caption_ok = (
        opening.get("mask_narration_captions_present") is True
        and isinstance(mask_captions, list)
        and len(mask_captions) >= 2
        and all(
            isinstance(item, dict)
            and bool(str(item.get("text") or "").strip())
            and as_float(item.get("start")) is not None
            and as_float(item.get("end")) is not None
            and float(item["end"]) > float(item["start"])
            and 0.05 <= float(item["start"]) < 2.90
            and float(item["end"]) <= 2.90
            for item in mask_captions
        )
    )
    add(checks, "opening_mask_narration_captions", mask_caption_ok, str(mask_captions))
    body_images = [path for path in (project / "08-正文画面").rglob("*") if path.suffix.lower() in image_suffixes]
    body_videos = [path for path in (project / "09-Grok视频").rglob("*") if path.suffix.lower() in video_suffixes]
    mask_content_ok = (
        (mask_image is None or content_is_distinct(mask_image, body_images))
        and content_is_distinct(mask_video, body_videos)
    )
    add(
        checks,
        "opening_mask_content_independent",
        mask_content_ok,
        f"遮罩视频对比 {len(body_videos)} 条正文视频；固定素材库模式不需要遮罩源图",
    )
    add(checks, "legacy_bridge_asset_absent", not opening.get("bridge_video_asset"), str(opening.get("bridge_video_asset")))
    add(checks, "expand_start", in_range(opening.get("expand_start"), 1.30, 1.45), str(opening.get("expand_start")))
    add(checks, "expand_end", in_range(opening.get("expand_end"), 2.80, 3.00), str(opening.get("expand_end")))
    add(checks, "carousel_start", in_range(opening.get("carousel_start"), 2.80, 3.00), str(opening.get("carousel_start")))
    durations = opening.get("card_durations", [])
    duration_values = [as_float(value) for value in durations] if isinstance(durations, list) else []
    carousel_plan: dict[str, Any] = {}
    opening_cards = opening.get("carousel_cards", [])
    expected_card_count = int(
        opening.get("carousel_count")
        or len(duration_values)
        or (len(opening_cards) if isinstance(opening_cards, list) else 0)
    )
    plan_path: Path | None = None
    dynamic_carousel = content_contract_version >= 4 or bool(str(opening.get("carousel_plan_asset") or ""))
    if dynamic_carousel:
        plan_value = str(opening.get("carousel_plan_asset") or "")
        plan_path = project / plan_value
        if plan_path.is_file():
            carousel_plan = read_json(plan_path)
        expected_card_count = int(carousel_plan.get("card_count") or 0)
        plan_ok = (
            bool(plan_value)
            and plan_path.is_file()
            and carousel_plan.get("mode") == "voice_timing_derived"
            and carousel_plan.get("timing_source_type") == "voice_actual"
            and carousel_plan.get("needs_actual_timing_replan") is False
            and int(carousel_plan.get("fps") or 0) == 30
            and int(carousel_plan.get("target_cover_lead_frames") or 0) == 0
            and carousel_plan.get("card_frame_range") == [3, 4]
            and expected_card_count >= 6
        )
        add(checks, "dynamic_carousel_plan", plan_ok, str(plan_path) if plan_value else "缺失")
        add(
            checks,
            "dynamic_carousel_count",
            int(opening.get("carousel_count") or 0) == expected_card_count,
            f"opening={opening.get('carousel_count')} / plan={expected_card_count}",
        )
    durations_ok = (
        len(duration_values) == expected_card_count
        and expected_card_count > 0
        and all(
            value is not None
            and round(value * 30) in {3, 4}
            and abs(value - round(value * 30) / 30) <= 0.001
            for value in duration_values
        )
    )
    add(checks, "card_durations", durations_ok, str(durations))
    carousel_start = as_float(opening.get("carousel_start"))
    carousel_end = as_float(opening.get("carousel_end"))
    duration_sum_ok = (
        durations_ok
        and carousel_start is not None
        and carousel_end is not None
        and abs(sum(value for value in duration_values if value is not None) - (carousel_end - carousel_start)) <= 0.08
    )
    add(checks, "carousel_duration_sum", duration_sum_ok, f"卡片 {sum(value for value in duration_values if value is not None):.2f}s / 区间 {((carousel_end or 0) - (carousel_start or 0)):.2f}s")
    carousel_motion = opening.get("carousel_motion", {})
    carousel_motion_ok = (
        carousel_motion.get("type") == "snap_settle"
        and 1.03 <= float(carousel_motion.get("scale_start", 0)) <= 1.04
        and float(carousel_motion.get("scale_end", 0)) == 1.0
        and 1.0 <= float(carousel_motion.get("soft_focus_px", 0)) <= 2.0
        and carousel_motion.get("transition") == "hard_cut"
    )
    add(checks, "carousel_snap_settle", carousel_motion_ok, str(carousel_motion))

    cards = opening.get("carousel_cards", [])
    cards_ok = isinstance(cards, list) and len(cards) == expected_card_count
    target = normalized_book_title(target_title)
    invalid_cards: list[str] = []
    if cards_ok:
        for index, card in enumerate(cards, start=1):
            if not isinstance(card, dict):
                invalid_cards.append(f"#{index}:not_object")
                continue
            asset = project / str(card.get("asset", ""))
            title = normalized_book_title(card.get("title"))
            if card.get("role") != "carousel" or not title or title == target or not asset.is_file():
                invalid_cards.append(f"#{index}:{title or 'missing'}")
    add(checks, "carousel_cards", cards_ok and not invalid_cards, f"违规 {invalid_cards}" if invalid_cards else f"{len(cards) if isinstance(cards, list) else 0} 张非目标真实书封卡")

    if dynamic_carousel:
        plan_frames = carousel_plan.get("card_frames", [])
        plan_durations = carousel_plan.get("card_durations", [])
        title_start_seconds = as_float(carousel_plan.get("title_start_seconds"))
        delivery_title_start = as_float(opening.get("book_title_delivery", {}).get("title_start_seconds"))
        target_cover_lead = None if title_start_seconds is None or carousel_end is None else title_start_seconds - carousel_end
        carousel_plan_timing_ok = (
            carousel_start is not None
            and carousel_end is not None
            and as_float(carousel_plan.get("carousel_start")) is not None
            and as_float(carousel_plan.get("carousel_end")) is not None
            and abs(carousel_start - float(carousel_plan["carousel_start"])) <= (1 / 30 + 0.001)
            and abs(carousel_end - float(carousel_plan["carousel_end"])) <= (1 / 30 + 0.001)
            and plan_frames == [round(value * 30) for value in duration_values]
            and len(plan_durations) == expected_card_count
            and target_cover_lead is not None
            and abs(target_cover_lead) <= (1 / 30 + 0.001)
            and delivery_title_start is not None
            and abs(delivery_title_start - title_start_seconds) <= (1 / 30 + 0.001)
        )
        add(
            checks,
            "carousel_lands_on_title",
            carousel_plan_timing_ok,
            f"书名 {title_start_seconds}s / 目标封面 {carousel_end}s / 提前 {target_cover_lead}s",
        )

    cover_hold_start = as_float(opening.get("target_cover_hold_start"))
    cover_hold_end = as_float(opening.get("target_cover_hold_end"))
    cover_hold_duration = None if cover_hold_start is None or cover_hold_end is None else cover_hold_end - cover_hold_start
    cover_hold_ok = (
        cover_hold_duration is not None
        and 0.65 <= cover_hold_duration <= 0.85
        and carousel_end is not None
        and abs(cover_hold_start - carousel_end) <= (1 / 30 + 0.001)
    )
    add(checks, "target_cover_hold", cover_hold_ok, f"{cover_hold_duration:.3f}s" if cover_hold_duration is not None else "missing")
    target_cover_base_asset = project / str(opening.get("target_cover_base_asset", ""))
    target_cover_title_page_asset = project / str(opening.get("target_cover_title_page_asset", ""))
    title_binding = opening.get("target_cover_title_binding", {})
    if dynamic_carousel:
        dynamic_lock_start = as_float(opening.get("target_lock_start"))
        add(
            checks,
            "target_lock_start",
            dynamic_lock_start is not None
            and cover_hold_end is not None
            and abs(dynamic_lock_start - cover_hold_end) <= (1 / 30 + 0.001),
            str(opening.get("target_lock_start")),
        )
    else:
        add(checks, "target_lock_start", in_range(opening.get("target_lock_start"), 4.75, 4.95), str(opening.get("target_lock_start")))
    add(checks, "target_lock_mode", opening.get("target_lock_mode") == "cover_waterwave_then_title_drop", str(opening.get("target_lock_mode")))
    target_hero = opening.get("target_hero_asset")
    add(checks, "target_hero_asset", bool(target_hero) and (project / str(target_hero)).is_file(), str(target_hero))
    target_lock_hold_asset = project / str(opening.get("target_lock_hold_asset", ""))
    title_voice_start = as_float(opening.get("book_title_voice_start"))
    title_voice_end = as_float(opening.get("book_title_voice_end"))
    target_lock_end_value = as_float(opening.get("target_lock_end"))
    body_voice_start_value = as_float(opening.get("body_voice_start"))
    cover_persistence_ok = (
        opening.get("cover_persists_until_body") is True
        and target_lock_hold_asset.is_file()
        and target_lock_hold_asset.resolve() == target_cover_title_page_asset.resolve()
        and title_voice_start is not None
        and title_voice_end is not None
        and cover_hold_start is not None
        and cover_hold_start <= title_voice_start < title_voice_end
        and target_lock_end_value is not None
        and body_voice_start_value is not None
        and title_voice_end <= target_lock_end_value
        and abs(target_lock_end_value - body_voice_start_value) <= TIMING_TOLERANCE_SECONDS
    )
    add(checks, "target_cover_persists_through_title", cover_persistence_ok, str(opening.get("target_lock_hold_asset")))
    title_motion = opening.get("title_motion", {})
    title_motion_ok = (
        title_motion.get("type") == "cover_page_title_settle"
        and 10 <= int(title_motion.get("settle_frames", 0)) <= 14
        and title_motion.get("easing") == "ease_out_cubic"
        and title_motion.get("start_anchor") == "cover_page_upper_center"
        and title_motion.get("end_anchor") == "cover_page_top"
    )
    add(checks, "waterdrop_title_motion", title_motion_ok, str(title_motion))
    water_effect = opening.get("waterdrop_lock_response", {})
    visual_start = as_float(water_effect.get("visual_start"))
    wave_trigger_at = as_float(water_effect.get("wave_trigger_at"))
    water_sfx_at = as_float(water_effect.get("sfx_at"))
    visual_end = as_float(water_effect.get("visual_end"))
    cover_release_at = as_float(water_effect.get("cover_release_at"))
    target_lock_start = as_float(opening.get("target_lock_start"))
    target_lock_end_for_water = as_float(opening.get("target_lock_end"))
    body_voice_start_for_water = as_float(opening.get("body_voice_start"))
    water_effect_asset = project / str(water_effect.get("effect_asset", ""))
    title_keyframes = water_effect.get("title_keyframes", [])
    expected_frames = [0, 1, 2]
    keyframes_ok = (
        isinstance(title_keyframes, list)
        and len(title_keyframes) >= 6
        and [int(item.get("frame", -1)) for item in title_keyframes[:3]] == expected_frames
        and 10 <= int(title_keyframes[-1].get("frame", 0)) <= 14
        and 0.30 <= float(title_keyframes[0].get("opacity", 0)) <= 0.55
        and 0.45 <= float(title_keyframes[1].get("opacity", 0)) <= 0.75
        and float(title_keyframes[2].get("opacity", 0)) == 1.0
        and float(title_keyframes[-1].get("opacity", 0)) == 1.0
        and 1.35 <= float(title_keyframes[0].get("scale", 0)) <= 1.55
        and 1.20 <= float(title_keyframes[2].get("scale", 0)) <= 1.45
        and float(title_keyframes[-1].get("scale", 0)) == 1.0
        and 2.0 <= float(title_keyframes[0].get("blur_px", 0)) <= 3.5
        and float(title_keyframes[-1].get("blur_px", -1)) == 0.0
        and 110 <= float(title_keyframes[0].get("y_px", 0)) <= 180
        and 50 <= float(title_keyframes[-1].get("y_px", 999)) <= 100
        and -0.70 <= float(title_keyframes[0].get("transform_y", 9)) <= -0.50
        and float(title_keyframes[-1].get("transform_y", 9)) <= -0.75
    )
    title_start = as_float(title_binding.get("title_start"))
    title_settle_end = as_float(title_binding.get("title_settle_end"))
    title_safe_area = title_binding.get("title_safe_area", {})
    cover_safe_area = title_binding.get("cover_safe_area", {})
    source_page_asset = project / str(water_effect.get("source_page_asset", ""))
    title_same_page_ok = (
        title_binding.get("mode") == "same_page_as_cover"
        and target_cover_base_asset.is_file()
        and target_cover_title_page_asset.is_file()
        and source_page_asset.resolve() == target_cover_title_page_asset.resolve()
        and water_effect.get("includes_title_layer") is True
        and title_binding.get("title_above_cover") is True
        and title_binding.get("cover_visible_during_title_motion") is True
        and title_binding.get("visible_through_waterwave") is True
        and title_binding.get("cover_visible_while_title_spoken") is True
        and title_binding.get("persist_to_body") is True
        and title_start is not None
        and cover_hold_start is not None
        and abs(title_start - cover_hold_start) <= (1 / 30 + 0.001)
        and title_settle_end is not None
        and title_start < title_settle_end <= (wave_trigger_at or -1) + 0.001
        and 40 <= float(title_safe_area.get("top", -1)) < float(title_safe_area.get("bottom", -1)) <= 240
        and float(title_safe_area.get("bottom", 9999)) < float(cover_safe_area.get("top", -1))
        and 220 <= float(cover_safe_area.get("top", -1)) < float(cover_safe_area.get("bottom", -1)) <= 1380
    )
    add(checks, "target_cover_title_same_page", title_same_page_ok, str(title_binding))
    water_timing_ok = (
        visual_start is not None
        and wave_trigger_at is not None
        and water_sfx_at is not None
        and visual_end is not None
        and cover_release_at is not None
        and target_lock_start is not None
        and target_lock_end_for_water is not None
        and body_voice_start_for_water is not None
        and cover_hold_start is not None
        and cover_hold_end is not None
        and cover_hold_start <= visual_start <= wave_trigger_at < visual_end <= cover_hold_end + 0.001
        and abs(visual_start - wave_trigger_at) <= (1 / 30 + 0.001)
        and abs(water_sfx_at - wave_trigger_at) <= (1 / 30 + 0.001)
        and 0.30 <= visual_end - wave_trigger_at <= 0.50
        and visual_end <= target_lock_start + (1 / 30 + 0.001)
        and target_lock_start <= cover_hold_end + (1 / 30 + 0.001)
        and abs(cover_release_at - target_lock_end_for_water) <= TIMING_TOLERANCE_SECONDS
        and abs(cover_release_at - body_voice_start_for_water) <= TIMING_TOLERANCE_SECONDS
    )
    waterdrop_lock_ok = (
        water_effect.get("type") == "cover_waterwave_then_title_drop"
        and water_effect.get("effect_on") == "entire_page"
        and water_effect.get("effect_style") == "full_frame_displacement_map"
        and water_effect.get("effect_scope") == "entire_page"
        and water_effect_asset.is_file()
        and water_effect_asset.suffix.lower() == ".mp4"
        and water_effect.get("includes_title_layer") is True
        and source_page_asset.is_file()
        and source_page_asset.resolve() == target_cover_title_page_asset.resolve()
        and water_effect.get("literal_water_graphic") is False
        and water_effect.get("overlay_graphic") is False
        and water_effect.get("visible_ring") is False
        and water_effect.get("page_deformation") is True
        and water_effect.get("refraction") is True
        and water_effect.get("perceptible_motion") is True
        and water_timing_ok
        and keyframes_ok
    )
    add(checks, "waterwave_full_page_sequence", waterdrop_lock_ok, str(water_effect))
    add(checks, "waterwave_page_asset", water_effect_asset.is_file(), str(water_effect_asset))
    add(checks, "waterwave_sound_on_cover", water_timing_ok, f"effect/trigger/sfx={visual_start}/{wave_trigger_at}/{water_sfx_at}, cover_release={cover_release_at}")
    if dynamic_carousel:
        delivery = opening.get("book_title_delivery", {})
        delivery_body_start = as_float(delivery.get("body_start_seconds"))
        dynamic_body_ok = (
            target_lock_end_value is not None
            and body_voice_start_value is not None
            and delivery_body_start is not None
            and abs(target_lock_end_value - body_voice_start_value) <= TIMING_TOLERANCE_SECONDS
            and abs(body_voice_start_value - delivery_body_start) <= TIMING_TOLERANCE_SECONDS
        )
        add(checks, "target_lock_end", dynamic_body_ok, str(opening.get("target_lock_end")))
        add(checks, "body_voice_start", dynamic_body_ok, str(opening.get("body_voice_start")))
    else:
        add(checks, "target_lock_end", in_range(opening.get("target_lock_end"), 5.30, 5.85), str(opening.get("target_lock_end")))
        add(checks, "body_voice_start", in_range(opening.get("body_voice_start"), 5.30, 5.85), str(opening.get("body_voice_start")))


def main() -> int:
    parser = argparse.ArgumentParser(description="验证情绪读书视频项目")
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument(
        "--stage",
        choices=["content_package", "sound_package", "visual_package", "timeline_package", "final_video", "jianying_draft", "full"],
        default="full",
        help="验证六关流程中的某个审核包，或全部交付物",
    )
    parser.add_argument("--video", type=Path, help="最终交付 MP4；时间轴关卡未指定时自动校验最新过程预览")
    parser.add_argument("--draft", type=Path, help="最终剪映草稿目录")
    args = parser.parse_args()

    project = args.project.resolve()
    checks: list[dict[str, Any]] = []
    manifest_path = project / "manifest.json"
    add(checks, "manifest", manifest_path.is_file(), str(manifest_path))
    if not manifest_path.is_file():
        print(json.dumps({"status": "FAIL", "checks": checks}, ensure_ascii=False, indent=2))
        return 1

    manifest = read_json(manifest_path)
    add(checks, "schema_version", manifest.get("schema_version") == 8, str(manifest.get("schema_version")))
    defaults = manifest.get("defaults", {})
    default_voice = defaults.get("voice", {})
    add(
        checks,
        "manifest_default_voice",
        default_voice.get("speaker") == DEFAULT_VOICE_SPEAKER
        and default_voice.get("selection_mode") == "default"
        and default_voice.get("speed_mode") == "reference_locked"
        and str(default_voice.get("reference_video_id")) == REFERENCE_SPEED_VIDEO_ID
        and as_float(default_voice.get("provider_speech_rate")) == FIXED_PROVIDER_SPEECH_RATE
        and as_float(default_voice.get("target_chars_per_second")) == FIXED_VOICE_CPS
        and as_float(default_voice.get("tolerance_chars_per_second")) == FIXED_VOICE_CPS_TOLERANCE,
        f"{default_voice.get('speaker')} / {default_voice.get('selection_mode')} / "
        f"{default_voice.get('speed_mode')} / {default_voice.get('target_chars_per_second')} 字/秒",
    )
    image_generation = defaults.get("image_generation")
    if isinstance(image_generation, dict):
        provider = image_generation.get("provider")
        selection_mode = image_generation.get("selection_mode")
        override_reason = str(image_generation.get("override_reason") or "").strip()
        image_policy_ok = valid_image_policy(image_generation)
        add(checks, "manifest_image_provider", image_policy_ok, f"{provider} / {selection_mode} / {override_reason}")
    video_generation = defaults.get("video_generation")
    if isinstance(video_generation, dict):
        video_provider = video_generation.get("provider")
        common_video_policy_ok = video_generation.get("motion_profile") == "restrained_micro_motion"
        if video_provider == DEFAULT_VIDEO_PROVIDER:
            video_policy_ok = (
                common_video_policy_ok
                and video_generation.get("bridge") == "grok-local"
                and video_generation.get("model") == "grok-imagine-video-via-cli"
                and video_generation.get("mode") == "reference_to_video"
                and video_generation.get("auth_mode") == "membership_oauth_only"
                and video_generation.get("selection_mode") == "default"
            )
        elif video_provider == "ltx_local":
            video_policy_ok = (
                common_video_policy_ok
                and video_generation.get("model") == "prince-canuma/LTX-2.3-dev"
                and video_generation.get("text_encoder") == "mlx-community/gemma-3-12b-it-4bit"
                and video_generation.get("pipeline") == "dev-two-stage-hq"
                and video_generation.get("probe_status") == "approved"
                and video_generation.get("selection_mode") == "user_override"
            )
        else:
            video_policy_ok = (
                video_provider == "ffmpeg_fallback"
                and common_video_policy_ok
                and video_generation.get("selection_mode") == "fallback"
            )
        add(checks, "manifest_video_provider", video_policy_ok, str(video_generation))
    typography = defaults.get("typography")
    if isinstance(typography, dict):
        skill_root = Path(__file__).resolve().parents[1]
        font_asset_value = str(typography.get("chinese_font_asset") or "")
        font_asset = skill_root / font_asset_value
        font_ok = (
            typography.get("chinese_font_id") == DEFAULT_CHINESE_FONT_ID
            and font_asset_value == DEFAULT_CHINESE_FONT_ASSET
            and font_asset.is_file()
            and sha256(font_asset) == DEFAULT_CHINESE_FONT_SHA256
            and typography.get("english_font_family") == "Georgia"
        )
        add(checks, "manifest_typography", font_ok, f"{typography.get('chinese_font_id')} / {font_asset_value}")
    content_policy = defaults.get("content")
    content_contract_version = 1
    if isinstance(content_policy, dict):
        content_contract_version = int(content_policy.get("contract_version") or 1)
        policy_max_seconds = as_float(content_policy.get("max_script_seconds"))
        policy_override = str(content_policy.get("duration_override") or "").strip()
        configured_forbidden = set(content_policy.get("forbidden_confirmation_openings", []))
        content_policy_ok = (
            content_policy.get("entry_mode") == "direct_theme"
            and policy_max_seconds is not None
            and policy_max_seconds == DEFAULT_MAX_SCRIPT_SECONDS
            and content_policy.get("preferred_han_count") == DEFAULT_PREFERRED_SCRIPT_HAN
            and content_policy.get("target_han_count") == DEFAULT_TARGET_SCRIPT_HAN
            and content_policy.get("max_han_count") == DEFAULT_MAX_SCRIPT_HAN
            and content_policy.get("segment_han_targets") == DEFAULT_SEGMENT_HAN_TARGETS
            and FORBIDDEN_CONFIRMATION_OPENINGS.issubset(configured_forbidden)
            and not policy_override
        )
        add(
            checks,
            "manifest_content_policy",
            content_policy_ok,
            f"{content_policy.get('entry_mode')} / {policy_max_seconds}s / override={policy_override or 'none'}",
        )
        if content_contract_version >= 2:
            mask_preview_policy_ok = (
                content_policy.get("mask_keyword_han_count") == 2
                and content_policy.get("mask_preview_required") is True
                and content_policy.get("mask_approval_stage") == "content_package"
            )
            add(
                checks,
                "manifest_content_mask_policy",
                mask_preview_policy_ok,
                f"{content_policy.get('mask_keyword_han_count')} 字 / {content_policy.get('mask_approval_stage')}",
            )
        if content_contract_version >= 3:
            book_delivery_policy = content_policy.get("book_title_delivery", {})
            book_pause_policy_ok = (
                content_policy.get("book_lead_template") == "今天分享的是，《{title}》。"
                and book_delivery_policy.get("lead_text") == BOOK_LEAD_TEXT
                and book_delivery_policy.get("pre_title_pause_seconds") == BOOK_TITLE_PRE_PAUSE_RANGE
                and as_float(book_delivery_policy.get("pre_title_target_seconds")) == BOOK_TITLE_PRE_PAUSE_TARGET
                and book_delivery_policy.get("post_title_pause_seconds") == BOOK_TITLE_POST_PAUSE_RANGE
                and as_float(book_delivery_policy.get("post_title_target_seconds")) == BOOK_TITLE_POST_PAUSE_TARGET
                and book_delivery_policy.get("title_emphasis") == BOOK_TITLE_EMPHASIS
                and book_delivery_policy.get("timing_evidence_required") is True
                and book_delivery_policy.get("fallback") == "pause_only_postprocess"
            )
            add(checks, "manifest_book_title_pause_policy", book_pause_policy_ok, str(book_delivery_policy))
        if content_contract_version >= 4:
            carousel_policy = content_policy.get("carousel_timing", {})
            add(
                checks,
                "manifest_dynamic_carousel_policy",
                carousel_policy == DEFAULT_CAROUSEL_TIMING,
                str(carousel_policy),
            )
    music_policy = defaults.get("music")
    if isinstance(music_policy, dict):
        add(
            checks,
            "manifest_music_policy",
            music_policy.get("selection_mode") == "user_provided_library_only"
            and music_policy.get("library_manifest") == "assets/bgm-library/library.json"
            and music_policy.get("required_source_scope") == "user_provided_local_file",
            str(music_policy),
        )
    parallel_policy = defaults.get("parallel_pipeline")
    add(
        checks,
        "manifest_parallel_pipeline",
        parallel_policy in (DEFAULT_PARALLEL_PIPELINE, LEGACY_PARALLEL_PIPELINE),
        str(parallel_policy),
    )
    delivery_policy = defaults.get("delivery")
    add(
        checks,
        "manifest_delivery_profile",
        delivery_policy == DEFAULT_DELIVERY,
        str(delivery_policy),
    )
    expected_gates = {
        "content_package",
        "sound_package",
        "visual_package",
        "timeline_package",
        "final_video",
        "jianying_draft",
    }
    actual_gates = set(manifest.get("steps", {}))
    add(checks, "confirmation_gates", actual_gates == expected_gates, str(sorted(actual_gates)))
    duration_config = manifest.get("duration", {})
    duration_mode = duration_config.get("mode")
    duration_requested = duration_config.get("requested")
    duration_estimated = duration_config.get("estimated")
    duration_locked = duration_config.get("locked")
    add(checks, "duration_mode", duration_mode in {"adaptive", "fixed"}, str(duration_mode))
    add(
        checks,
        "duration_request",
        (duration_mode == "adaptive" and duration_requested is None)
        or (duration_mode == "fixed" and duration_requested is not None and float(duration_requested) > 0),
        str(duration_requested),
    )
    canvas = manifest.get("canvas", {})
    add(
        checks,
        "manifest_canvas",
        (canvas.get("width"), canvas.get("height"), canvas.get("fps")) == (1080, 1440, 30),
        f"{canvas.get('width')}x{canvas.get('height')}@{canvas.get('fps')}",
    )

    book_path = newest(project / "01-书籍资料", "book-v*.json")
    sources_path = newest(project / "01-书籍资料", "sources-v*.md")
    cover_candidates = sorted(
        path
        for pattern in ("cover-v*.jpg", "cover-v*.jpeg", "cover-v*.png", "cover-v*.webp")
        for path in (project / "01-书籍资料").glob(pattern)
    )
    cover_path = cover_candidates[-1] if cover_candidates else None
    emotion_path = newest(project / "02-情绪提炼", "emotion-map-v*.md")
    content_mask_record_path = newest(project / "02-情绪提炼", "mask-keyword-v*.json")
    add(checks, "book_file", book_path is not None, str(book_path) if book_path else "未找到")
    add(checks, "sources_file", sources_path is not None, str(sources_path) if sources_path else "未找到")
    add(checks, "cover_file", cover_path is not None, str(cover_path) if cover_path else "未找到")
    add(checks, "emotion_map", emotion_path is not None, str(emotion_path) if emotion_path else "未找到")
    book: dict[str, Any] = {}
    if book_path:
        book = read_json(book_path)
        identity_ok = bool(str(book.get("title", "")).strip()) and bool(str(book.get("author", "")).strip())
        points = book.get("verified_points", [])
        add(checks, "book_identity", identity_ok, f"{book.get('title', '')} / {book.get('author', '')}")
        add(checks, "verified_points", isinstance(points, list) and len(points) >= 3, f"{len(points) if isinstance(points, list) else 0} 个")
    if sources_path:
        source_text = sources_path.read_text(encoding="utf-8")
        source_links = len(re.findall(r"https://", source_text))
        add(checks, "source_links", source_links >= 3, f"{source_links} 个可追溯链接")
    if emotion_path:
        emotion_text = emotion_path.read_text(encoding="utf-8")
        emotion_ok = "主情绪" in emotion_text and "核心命题" in emotion_text
        add(checks, "selected_emotion", emotion_ok, "已写入唯一主情绪和核心命题" if emotion_ok else "缺少主情绪或核心命题")

    content_mask_record: dict[str, Any] = {}
    content_mask_alpha: Path | None = None
    content_mask_preview: Path | None = None
    if content_contract_version >= 2:
        add(
            checks,
            "content_mask_record",
            content_mask_record_path is not None,
            str(content_mask_record_path) if content_mask_record_path else "未找到",
        )
        if content_mask_record_path:
            content_mask_record = read_json(content_mask_record_path)
            content_mask_alpha = resolve_project_asset(project, content_mask_record.get("alpha_mask"))
            content_mask_preview = resolve_project_asset(project, content_mask_record.get("preview"))
            keyword = str(content_mask_record.get("keyword") or "")
            exact_two = bool(re.fullmatch(r"[\u3400-\u9fff]{2}", keyword)) and content_mask_record.get("han_count") == 2
            add(checks, "content_mask_keyword_exact_two", exact_two, f"{keyword} / {content_mask_record.get('han_count')} 字")
            record_contract_ok = (
                content_mask_record.get("approval_stage") == "content_package"
                and content_mask_record.get("preview_type") == "actual_alpha_mask_confirmation"
                and content_mask_record.get("review_status") in {"awaiting_confirmation", "confirmed"}
                and content_mask_record.get("downstream_policy") == "reuse_exact_approved_mask"
            )
            add(checks, "content_mask_record_contract", record_contract_ok, str(content_mask_record.get("review_status")))
            mask_root = project / "02-情绪提炼"
            paths_ok = (
                is_within(content_mask_alpha, mask_root)
                and is_within(content_mask_preview, mask_root)
                and content_mask_alpha.is_file()
                and content_mask_preview.is_file()
            )
            add(checks, "content_mask_assets", paths_ok, f"{content_mask_alpha} / {content_mask_preview}")
            if paths_ok:
                try:
                    with Image.open(content_mask_alpha) as alpha_image, Image.open(content_mask_preview) as preview_image:
                        alpha_gray = alpha_image.convert("L")
                        alpha_ok = alpha_gray.size == (1080, 1440) and sum(alpha_gray.histogram()[17:]) >= 1000
                        preview_ok = preview_image.size == (1080, 1440)
                    add(checks, "content_mask_alpha_image", alpha_ok, f"{alpha_gray.size[0]}x{alpha_gray.size[1]}")
                    add(checks, "content_mask_preview_image", preview_ok, f"{preview_image.size[0]}x{preview_image.size[1]}")
                except OSError as exc:
                    add(checks, "content_mask_images", False, str(exc))

    script_path = newest(project / "03-逐字稿", "script-v*.json")
    originality_path = newest(project / "03-逐字稿", "originality-check-v*.md")
    add(checks, "script_file", script_path is not None, str(script_path) if script_path else "未找到")
    add(checks, "originality_check", originality_path is not None, str(originality_path) if originality_path else "未找到")
    script: dict[str, Any] = {}
    if script_path:
        script = read_json(script_path)
        add(checks, "script_structure", script.get("script_structure") == "moyan_emotional_v1", str(script.get("script_structure")))
        add(
            checks,
            "reference_thread",
            script.get("reference_thread_id") == "019fb90e-e259-7fa0-b0b5-1ce0c8179a03",
            str(script.get("reference_thread_id")),
        )
        quote_mode = script.get("quote_mode")
        add(checks, "quote_mode", quote_mode in {"verified_quote", "interpretation"}, str(quote_mode))
        add(checks, "sources", bool(script.get("source_refs")), f"{len(script.get('source_refs', []))} 个来源")
        segments = script.get("segments", [])
        if content_contract_version >= 3:
            verified_title = str(book.get("title") or "").strip().strip("《》")
            expected_book_lead = f"今天分享的是，《{verified_title}》。"
            book_delivery = script.get("book_lead_delivery", {})
            tts_lines = [line.strip() for line in str(book_delivery.get("tts_text") or "").splitlines() if line.strip()]
            tts_structure_ok = (
                len(tts_lines) == 2
                and tts_lines[0] == "今天分享的是，"
                and tts_lines[1].strip("《》") == f"{verified_title}。"
            )
            book_lead_contract_ok = (
                bool(verified_title)
                and script.get("book_lead") == expected_book_lead
                and book_delivery.get("lead_text") == BOOK_LEAD_TEXT
                and str(book_delivery.get("title_text") or "").strip().strip("《》") == verified_title
                and tts_structure_ok
                and book_delivery.get("pre_title_pause_seconds") == BOOK_TITLE_PRE_PAUSE_RANGE
                and as_float(book_delivery.get("pre_title_target_seconds")) == BOOK_TITLE_PRE_PAUSE_TARGET
                and book_delivery.get("post_title_pause_seconds") == BOOK_TITLE_POST_PAUSE_RANGE
                and as_float(book_delivery.get("post_title_target_seconds")) == BOOK_TITLE_POST_PAUSE_TARGET
                and book_delivery.get("title_emphasis") == BOOK_TITLE_EMPHASIS
                and book_delivery.get("fallback") == "pause_only_postprocess"
            )
            add(
                checks,
                "script_book_title_pause_contract",
                book_lead_contract_ok,
                f"{script.get('book_lead')} / {book_delivery}",
            )
        full_text = "".join(
            [script.get("hook", ""), script.get("book_lead", "")]
            + [segment.get("text", "") for segment in segments]
        )
        author_names: set[str] = set()
        for raw_name in (book.get("author"), book.get("author_original")):
            name = str(raw_name or "").strip()
            if not name:
                continue
            author_names.add(name.lower())
            author_names.update(
                part.lower()
                for part in re.split(r"[\s·•・]+", name)
                if len(part.strip()) >= 2
            )
        spoken_lower = full_text.lower()
        spoken_authors = sorted(name for name in author_names if name in spoken_lower)
        add(
            checks,
            "spoken_no_author",
            not spoken_authors and "作者" not in full_text,
            f"命中 {spoken_authors}" if spoken_authors else "口播未提作者",
        )
        lecture_terms = {
            "书中写到",
            "书中写道",
            "书中提到",
            "书里说",
            "这本书告诉",
            "这本书让我",
            "从这本书",
            "讨论群体",
            "作者认为",
            "作者指出",
        }
        lecture_hits = sorted(term for term in lecture_terms if term in full_text)
        add(
            checks,
            "spoken_no_lecture_voice",
            not lecture_hits,
            f"命中 {lecture_hits}" if lecture_hits else "没有书籍讲解腔",
        )
        chars = han_count(full_text)
        script_duration_mode = script.get("duration_mode")
        planned_duration = float(
            script.get("duration_target")
            if script_duration_mode == "fixed"
            else script.get("duration_estimate") or 0
        )
        cps = chars / planned_duration if planned_duration else 0
        target_chars_for_duration = planned_duration * FIXED_VOICE_CPS
        duration_ok = planned_duration > 0
        add(checks, "script_duration_mode", script_duration_mode == duration_mode, f"{script_duration_mode} / {duration_mode}")
        add(checks, "duration_plan", duration_ok, f"{planned_duration:.2f} 秒")
        if isinstance(content_policy, dict):
            max_script_seconds = as_float(content_policy.get("max_script_seconds")) or DEFAULT_MAX_SCRIPT_SECONDS
            first_body = str(segments[0].get("text", "")).strip() if segments else ""
            opening_hits = sorted(term for term in FORBIDDEN_CONFIRMATION_OPENINGS if first_body.startswith(term))
            first_sentence = re.split(r"[。！？!?]", first_body, maxsplit=1)[0]
            direct_entry_ok = (
                script.get("entry_mode") == "direct_theme"
                and bool(first_body)
                and not opening_hits
                and "？" not in first_sentence
                and "?" not in first_sentence
            )
            add(
                checks,
                "direct_theme_entry",
                direct_entry_ok,
                f"entry_mode={script.get('entry_mode')} / 命中 {opening_hits}" if opening_hits else f"entry_mode={script.get('entry_mode')} / 直接陈述",
            )
            add(
                checks,
                "script_max_duration",
                planned_duration <= max_script_seconds + 0.01,
                f"{planned_duration:.2f} / 上限 {max_script_seconds:.2f} 秒",
            )
        if script_duration_mode == "adaptive":
            estimate_matches = duration_estimated is not None and abs(float(duration_estimated) - planned_duration) <= 0.5
            add(checks, "manifest_duration_estimate", estimate_matches, str(duration_estimated))
        add(
            checks,
            "han_count",
            chars <= DEFAULT_MAX_SCRIPT_HAN and abs(chars - target_chars_for_duration) <= 1.0,
            f"{chars} 个汉字 / 硬上限 {DEFAULT_MAX_SCRIPT_HAN} / 时长对应 {target_chars_for_duration:.1f}",
        )
        add(
            checks,
            "script_target_rate",
            as_float(script.get("target_chars_per_second")) == FIXED_VOICE_CPS,
            str(script.get("target_chars_per_second")),
        )
        add(
            checks,
            "speech_rate",
            abs(cps - FIXED_VOICE_CPS) <= FIXED_VOICE_CPS_TOLERANCE,
            f"{cps:.3f} 字/秒 / 锁定 {FIXED_VOICE_CPS:.2f}",
        )
        add(checks, "hook_length", 9 <= han_count(script.get("hook", "")) <= 22, f"{han_count(script.get('hook', ''))} 字")
        roles = {segment.get("role") for segment in script.get("segments", [])}
        required_roles = {
            "viewer_expression",
            "pressure_escalation",
            "cognitive_reversal",
            "action_permission",
            "identity_close",
        }
        add(checks, "emotion_arc", required_roles.issubset(roles), f"已有 {sorted(str(role) for role in roles)}")

        expected_timing_roles = ["hook", "book_lead"] + [
            "viewer_expression",
            "pressure_escalation",
            "cognitive_reversal",
            "action_permission",
            "identity_close",
        ]
        timing_plan = script.get("timing_plan", [])
        timing_roles = [item.get("role") for item in timing_plan if isinstance(item, dict)]
        timing_valid = timing_roles == expected_timing_roles
        timing_cursor = 0.0
        source_text_by_role = {
            "hook": script.get("hook", ""),
            "book_lead": script.get("book_lead", ""),
            **{
                str(segment.get("role")): segment.get("text", "")
                for segment in segments
                if isinstance(segment, dict)
            },
        }
        for item in timing_plan if isinstance(timing_plan, list) else []:
            if not isinstance(item, dict):
                timing_valid = False
                continue
            role = str(item.get("role") or "")
            item_chars = han_count(source_text_by_role.get(role, ""))
            item_duration = item_chars / FIXED_VOICE_CPS
            start = as_float(item.get("start_estimate"))
            end = as_float(item.get("end_estimate"))
            duration = as_float(item.get("duration_estimate"))
            if (
                item.get("han_count") != item_chars
                or start is None
                or end is None
                or duration is None
                or abs(start - timing_cursor) > 0.02
                or abs(duration - item_duration) > 0.02
                or abs(end - (start + duration)) > 0.02
            ):
                timing_valid = False
            if end is not None:
                timing_cursor = end
        add(
            checks,
            "script_segment_timing",
            timing_valid,
            f"{timing_roles} / 累计 {timing_cursor:.2f} 秒",
        )
        ending_tail_estimate = as_float(script.get("ending_tail_seconds"))
        video_duration_estimate = as_float(script.get("video_duration_estimate"))
        market_duration_ok = (
            ending_tail_estimate is not None
            and 0.2 <= ending_tail_estimate <= 0.5
            and video_duration_estimate is not None
            and abs(video_duration_estimate - (planned_duration + ending_tail_estimate)) <= 0.02
            and video_duration_estimate < DEFAULT_MAX_SCRIPT_SECONDS
        )
        add(
            checks,
            "market_duration_under_60s",
            market_duration_ok,
            f"{video_duration_estimate} 秒（含尾音 {ending_tail_estimate}秒）",
        )
        if content_contract_version >= 2 and content_mask_record:
            hook_matches = re.sub(r"\s+", "", str(content_mask_record.get("hook") or "")) == re.sub(
                r"\s+", "", str(script.get("hook") or "")
            )
            add(checks, "content_mask_hook_binding", hook_matches, str(content_mask_record.get("hook")))

    if args.stage == "content_package":
        content_step = manifest.get("steps", {}).get("content_package", {})
        content_status = content_step.get("status")
        add(
            checks,
            "content_package_review_ready",
            content_status in {"awaiting_confirmation", "confirmed"},
            str(content_status),
        )
        if content_contract_version >= 2:
            record_status = content_mask_record.get("review_status")
            expected_record_status = "confirmed" if content_status == "confirmed" else "awaiting_confirmation"
            add(
                checks,
                "content_mask_confirmation_state",
                record_status == expected_record_status,
                f"内容包 {content_status} / 遮罩 {record_status}",
            )
        artifacts = content_step.get("artifacts", [])
        missing_artifacts = [str(item) for item in artifacts if not (project / str(item)).is_file()]
        required_mask_artifacts: set[str] = set()
        if (
            content_contract_version >= 2
            and content_mask_record_path
            and content_mask_alpha
            and content_mask_preview
            and is_within(content_mask_record_path, project)
            and is_within(content_mask_alpha, project)
            and is_within(content_mask_preview, project)
        ):
            required_mask_artifacts = {
                str(content_mask_record_path.relative_to(project)),
                str(content_mask_alpha.relative_to(project)),
                str(content_mask_preview.relative_to(project)),
            }
        artifact_set = {str(item) for item in artifacts}
        artifacts_ok = (
            len(artifacts) >= (10 if content_contract_version >= 2 else 7)
            and not missing_artifacts
            and required_mask_artifacts.issubset(artifact_set)
        )
        add(
            checks,
            "content_package_artifacts",
            artifacts_ok,
            f"缺失 {missing_artifacts or sorted(required_mask_artifacts - artifact_set)}" if not artifacts_ok else f"{len(artifacts)} 个素材已落盘",
        )
        return finish(checks, args.stage)

    sound_blueprint = newest(project / "04-声音设计", "sound-blueprint-v*.json")
    add(checks, "sound_blueprint", sound_blueprint is not None, str(sound_blueprint) if sound_blueprint else "未找到")
    if sound_blueprint:
        sound = read_json(sound_blueprint)
        voice = sound.get("voice", {})
        music = sound.get("music", {})
        stages = {item.get("id") for item in sound.get("stages", [])}
        add(checks, "emotion_preset", sound.get("emotion_preset") in {"清醒型", "被理解型", "自救型"}, str(sound.get("emotion_preset")))
        add(checks, "primary_reference", bool(sound.get("primary_reference")), str(sound.get("primary_reference")))
        selection_mode = voice.get("selection_mode")
        override_reason = str(voice.get("override_reason") or "").strip()
        default_voice_ok = valid_voice_policy(voice)
        add(checks, "default_voice_policy", default_voice_ok, f"{voice.get('speaker')} / {selection_mode} / {override_reason}")
        add(checks, "continuous_voice", voice.get("generation_mode") == "continuous", str(voice.get("generation_mode")))
        fixed_blueprint_rate = (
            voice.get("speed_mode") == "reference_locked"
            and str(voice.get("reference_video_id")) == REFERENCE_SPEED_VIDEO_ID
            and as_float(voice.get("provider_speech_rate")) == FIXED_PROVIDER_SPEECH_RATE
            and as_float(voice.get("target_chars_per_second")) == FIXED_VOICE_CPS
            and as_float(voice.get("tolerance_chars_per_second")) == FIXED_VOICE_CPS_TOLERANCE
        )
        add(checks, "voice_rate", fixed_blueprint_rate, str(voice.get("target_chars_per_second")))
        if content_contract_version >= 3:
            blueprint_delivery = voice.get("book_title_delivery", {})
            blueprint_pause_ok = (
                blueprint_delivery.get("lead_text") == BOOK_LEAD_TEXT
                and blueprint_delivery.get("pre_title_pause_seconds") == BOOK_TITLE_PRE_PAUSE_RANGE
                and as_float(blueprint_delivery.get("pre_title_target_seconds")) == BOOK_TITLE_PRE_PAUSE_TARGET
                and blueprint_delivery.get("post_title_pause_seconds") == BOOK_TITLE_POST_PAUSE_RANGE
                and as_float(blueprint_delivery.get("post_title_target_seconds")) == BOOK_TITLE_POST_PAUSE_TARGET
                and blueprint_delivery.get("title_emphasis") == BOOK_TITLE_EMPHASIS
                and blueprint_delivery.get("fallback") == "pause_only_postprocess"
            )
            add(checks, "sound_book_title_pause_policy", blueprint_pause_ok, str(blueprint_delivery))
        if isinstance(music_policy, dict):
            skill_root = Path(__file__).resolve().parents[1]
            library_path = skill_root / str(music_policy.get("library_manifest"))
            library = read_json(library_path) if library_path.is_file() else {}
            library_entries = {
                str(item.get("id")): item
                for item in library.get("tracks", [])
                if isinstance(item, dict)
            }
            track_id = str(music.get("library_track_id") or "")
            track = library_entries.get(track_id, {})
            track_file = skill_root / "assets/bgm-library" / str(track.get("file") or "")
            library_source_ok = (
                library.get("selection_policy") == "user_provided_only"
                and music.get("selection_mode") == "ai_selected_from_user_library"
                and music.get("source_scope") == "user_provided_local_file"
                and track.get("source_scope") == "user_provided_local_file"
                and track.get("status") in {"available", "available_preview"}
                and track_file.is_file()
            )
            add(checks, "bgm_user_library_source", library_source_ok, f"{track_id} / {track_file}")
        vocal_exception = music.get("vocal_song_exception", {})
        music_policy_ok = music.get("lyrics") is False or (
            music.get("lyrics") is True
            and vocal_exception.get("enabled") is True
            and vocal_exception.get("user_selected") is True
        )
        add(
            checks,
            "music_vocal_policy",
            music_policy_ok,
            "instrumental" if music.get("lyrics") is False else str(vocal_exception),
        )
        opening_stage_ok = {"hook", "mask_expand", "carousel", "book_lock"}.issubset(stages)
        add(checks, "opening_sound_stages", opening_stage_ok, str(sorted(stages)))

        voice_selection_path = newest(project / "04-声音设计", "voice-selection-v*.json")
        add(checks, "voice_selection", voice_selection_path is not None, str(voice_selection_path) if voice_selection_path else "未找到")
        if voice_selection_path:
            selection = read_json(voice_selection_path)
            candidates = selection.get("candidates", [])
            candidate_speakers = {item.get("speaker") for item in candidates}
            candidate_rates = {as_float(item.get("speech_rate")) for item in candidates}
            selected_speaker = selection.get("selected_speaker")
            add(checks, "voice_candidates", len(candidates) >= 2, f"{len(candidates)} 个候选")
            add(checks, "selected_voice", selected_speaker in candidate_speakers and selected_speaker == voice.get("speaker"), str(selected_speaker))
            selection_policy_ok = valid_voice_selection_policy(selection, selection_mode)
            add(checks, "voice_selection_policy", selection_policy_ok, f"{selection.get('selection_mode')} / {selection.get('override_reason')}")
            add(
                checks,
                "voice_candidates_fixed_rate",
                candidate_rates == {float(FIXED_PROVIDER_SPEECH_RATE)}
                and as_float(selection.get("selected_speech_rate")) == FIXED_PROVIDER_SPEECH_RATE
                and as_float(selection.get("target_chars_per_second")) == FIXED_VOICE_CPS,
                f"候选 {sorted(str(rate) for rate in candidate_rates)} / 中选 {selection.get('selected_speech_rate')}",
            )

    voice_dir = project / "05-配音"
    raw_voice_path = newest(voice_dir, "voice-raw-v*.wav")
    voice_path = newest(voice_dir, "voice-v*.wav")
    timing_path = newest(voice_dir, "timing-v*.json")
    add(checks, "voice_raw_file", raw_voice_path is not None, str(raw_voice_path) if raw_voice_path else "未找到")
    add(checks, "voice_processed_file", voice_path is not None, str(voice_path) if voice_path else "未找到")
    add(checks, "voice_timing_file", timing_path is not None, str(timing_path) if timing_path else "未找到")
    if voice_path and timing_path:
        timing = read_json(timing_path)
        timing_duration = float(timing.get("duration_seconds", 0))
        timing_rate = float(timing.get("chars_per_second", 0))
        first_word = float(timing.get("first_word_start_seconds", -1))
        last_word = float(timing.get("last_word_end_seconds", -1))
        ending_tail = float(timing.get("ending_tail_seconds", -1))
        add(checks, "voice_generation_mode", timing.get("generation_mode") == "continuous_single_request", str(timing.get("generation_mode")))
        add(
            checks,
            "voice_speed_policy",
            timing.get("speed_mode") == "reference_locked"
            and str(timing.get("reference_video_id")) == REFERENCE_SPEED_VIDEO_ID
            and as_float(timing.get("provider_speech_rate")) == FIXED_PROVIDER_SPEECH_RATE
            and as_float(timing.get("target_chars_per_second")) == FIXED_VOICE_CPS,
            f"{timing.get('speed_mode')} / {timing.get('provider_speech_rate')} / {timing.get('target_chars_per_second')}",
        )
        add(
            checks,
            "voice_measured_rate",
            abs(timing_rate - FIXED_VOICE_CPS) <= FIXED_VOICE_CPS_TOLERANCE,
            f"{timing_rate:.3f} 字/秒 / 锁定 {FIXED_VOICE_CPS:.2f}",
        )
        add(checks, "voice_first_word", 0 <= first_word <= 0.12, f"{first_word:.3f} 秒")
        add(checks, "voice_last_word", first_word < last_word <= timing_duration, f"{last_word:.3f} 秒")
        add(checks, "voice_ending_tail", 0.2 <= ending_tail <= 0.5, f"{ending_tail:.3f} 秒")
        media = ffprobe(voice_path)
        media_duration = float(media.get("format", {}).get("duration", 0))
        add(checks, "voice_duration_matches_timing", abs(media_duration - timing_duration) <= 0.05, f"音频 {media_duration:.3f}s / 时间轴 {timing_duration:.3f}s")
        locked_duration = manifest.get("duration", {}).get("locked")
        add(checks, "manifest_locked_duration", locked_duration is not None and abs(float(locked_duration) - timing_duration) <= 0.05, str(locked_duration))
        qc = timing.get("qc", {})
        add(checks, "voice_script_alignment", qc.get("script_alignment_complete") is True, str(qc.get("script_alignment_complete")))
        if content_contract_version >= 3:
            delivery = timing.get("book_title_delivery", {})
            lead_end = as_float(delivery.get("lead_end_seconds"))
            title_start = as_float(delivery.get("title_start_seconds"))
            title_end = as_float(delivery.get("title_end_seconds"))
            body_start = as_float(delivery.get("body_start_seconds"))
            reported_pre_pause = as_float(delivery.get("pre_title_pause_seconds"))
            reported_post_pause = as_float(delivery.get("post_title_pause_seconds"))
            actual_pre_pause = (
                title_start - lead_end
                if title_start is not None and lead_end is not None
                else None
            )
            actual_post_pause = (
                body_start - title_end
                if body_start is not None and title_end is not None
                else None
            )
            timing_segments = [item for item in timing.get("segments", []) if isinstance(item, dict)]
            book_lead_segment = next((item for item in timing_segments if item.get("id") == "book_lead"), {})
            first_body_segment = next(
                (item for item in timing_segments if item.get("id") not in {"hook", "book_lead"}),
                {},
            )
            measured_pause_ok = (
                None not in {
                    lead_end,
                    title_start,
                    title_end,
                    body_start,
                    reported_pre_pause,
                    reported_post_pause,
                }
                and lead_end < title_start < title_end < body_start
                and BOOK_TITLE_PRE_PAUSE_RANGE[0] <= actual_pre_pause <= BOOK_TITLE_PRE_PAUSE_RANGE[1]
                and BOOK_TITLE_POST_PAUSE_RANGE[0] <= actual_post_pause <= BOOK_TITLE_POST_PAUSE_RANGE[1]
                and abs(reported_pre_pause - actual_pre_pause) <= 0.02
                and abs(reported_post_pause - actual_post_pause) <= 0.02
                and abs((as_float(book_lead_segment.get("end")) or -1) - title_end) <= TIMING_TOLERANCE_SECONDS
                and abs((as_float(first_body_segment.get("start")) or -1) - body_start) <= TIMING_TOLERANCE_SECONDS
            )
            delivery_metadata_ok = (
                delivery.get("lead_text") == BOOK_LEAD_TEXT
                and str(delivery.get("title_text") or "").strip().strip("《》") == str(book.get("title") or "").strip().strip("《》")
                and delivery.get("title_emphasis") == BOOK_TITLE_EMPHASIS
                and delivery.get("evidence_source") == "word_timestamps_and_waveform"
                and isinstance(delivery.get("pause_postprocess_applied"), bool)
            )
            add(
                checks,
                "voice_book_title_pauses",
                measured_pause_ok,
                f"前 {reported_pre_pause}s / 后 {reported_post_pause}s",
            )
            add(checks, "voice_book_title_delivery", delivery_metadata_ok, str(delivery))

    sound_step = manifest.get("steps", {}).get("sound_package", {})
    sound_artifacts = sound_step.get("artifacts", [])
    missing_sound_artifacts = [str(item) for item in sound_artifacts if not (project / str(item)).is_file()]
    add(
        checks,
        "sound_package_review_ready",
        sound_step.get("status") in {"awaiting_confirmation", "confirmed"},
        str(sound_step.get("status")),
    )
    add(
        checks,
        "sound_package_artifacts",
        len(sound_artifacts) >= 9 and not missing_sound_artifacts,
        f"缺失 {missing_sound_artifacts}" if missing_sound_artifacts else f"{len(sound_artifacts)} 个素材已落盘",
    )
    bgm_path = newest(project / "06-配乐音效", "bgm-v*.wav")
    music_source_path = newest(project / "06-配乐音效", "music-source-v*.md")
    music_cue_path = newest(project / "06-配乐音效", "music-cue-v*.json")
    mix_preview_path = newest(project / "06-配乐音效", "audio-mix-preview-v*.wav")
    add(checks, "bgm_file", bgm_path is not None, str(bgm_path) if bgm_path else "未找到")
    add(checks, "music_source", music_source_path is not None, str(music_source_path) if music_source_path else "未找到")
    add(checks, "music_cue", music_cue_path is not None, str(music_cue_path) if music_cue_path else "未找到")
    add(checks, "audio_mix_preview", mix_preview_path is not None, str(mix_preview_path) if mix_preview_path else "未找到")
    if music_cue_path:
        cue = read_json(music_cue_path)
        cue_music = cue.get("music", {})
        if cue_music.get("lyrics") is True or cue_music.get("vocal_samples") is True:
            exception = cue_music.get("vocal_song_exception", {})
            ducking = cue.get("ducking", {})
            bgm_lufs = float(cue_music.get("integrated_lufs", 0))
            duck_db = float(ducking.get("measured_integrated_reduction_db", 0))
            voice_lead_db = float(ducking.get("voice_lead_during_speech_db", 0))
            add(
                checks,
                "vocal_song_user_selected",
                exception.get("enabled") is True and exception.get("user_selected") is True,
                str(exception),
            )
            add(checks, "vocal_song_bgm_level", -28.5 <= bgm_lufs <= -21.0, f"{bgm_lufs:.1f} LUFS")
            add(checks, "vocal_song_ducking", 5.0 <= duck_db <= 8.0, f"{duck_db:.1f} dB")
            add(checks, "vocal_song_voice_lead", 10.0 <= voice_lead_db <= 14.0, f"{voice_lead_db:.1f} dB")
            add(
                checks,
                "vocal_song_treatment",
                bool(str(exception.get("vocal_treatment", "")).strip()),
                str(exception.get("vocal_treatment")),
            )
            add(
                checks,
                "vocal_song_lyrics_masked",
                exception.get("continuous_lyrics_intelligible_during_dialogue") is False,
                str(exception.get("continuous_lyrics_intelligible_during_dialogue")),
            )
    if args.stage == "sound_package":
        visual_status = manifest.get("steps", {}).get("visual_package", {}).get("status")
        paired_ready = sound_step.get("status") in {"awaiting_confirmation", "confirmed"} and visual_status in {"awaiting_confirmation", "confirmed"}
        add(checks, "sound_visual_paired_review", paired_ready, f"sound={sound_step.get('status')} / visual={visual_status}")
        pipeline_path = newest(project / "07-分镜", "parallel-pipeline-v*.json")
        add(checks, "parallel_pipeline_file", pipeline_path is not None, str(pipeline_path) if pipeline_path else "未找到")
        expected_shot_ids = {path.stem for path in (project / "08-正文画面").rglob("shot-*.png")}
        pipeline_errors = validate_parallel_pipeline_run(
            read_json(pipeline_path) if pipeline_path else None,
            project,
            script_path,
            expected_shot_ids,
        )
        add(checks, "parallel_pipeline_execution", not pipeline_errors, f"违规 {pipeline_errors}" if pipeline_errors else "四分支并行、逐图触发和实际时码汇合证据完整")
        return finish(checks, args.stage)

    grok_dir = project / "09-Grok视频"
    oauth_path = newest(grok_dir, "oauth-check-v*.json")
    plan_path = newest(grok_dir, "grok-video-plan-v*.json")
    add(checks, "grok_oauth_check", oauth_path is not None, str(oauth_path) if oauth_path else "未找到")
    add(checks, "grok_video_plan", plan_path is not None, str(plan_path) if plan_path else "未找到")
    grok_plan: dict[str, Any] = {}
    if oauth_path:
        oauth = read_json(oauth_path)
        add(checks, "oauth_mode", oauth.get("auth_mode") == "membership_oauth_only", str(oauth.get("auth_mode")))
        add(checks, "oauth_billing", oauth.get("billing_mode") == "subscription_allowance", str(oauth.get("billing_mode")))
        add(checks, "no_api_key_fallback", oauth.get("api_key_fallback") is False, str(oauth.get("api_key_fallback")))
        add(checks, "no_auto_top_up", oauth.get("auto_top_up") is False, str(oauth.get("auto_top_up")))
        leaked = find_secret_fields(oauth)
        add(checks, "oauth_secret_free", not leaked, f"敏感字段 {leaked}" if leaked else "未落盘凭证")
    if plan_path:
        grok_plan = read_json(plan_path)
        mode = grok_plan.get("mode")
        selected = grok_plan.get("selected_shots", [])
        add(checks, "grok_mode", mode in {"grok_oauth", "mixed", "ffmpeg_fallback"}, str(mode))
        add(checks, "grok_timing_basis", grok_plan.get("timing_basis") == "voice_actual", str(grok_plan.get("timing_basis")))
        add(checks, "grok_shot_list", isinstance(selected, list), f"{len(selected) if isinstance(selected, list) else '非数组'} 个")
        add(checks, "grok_model", mode not in {"grok_oauth", "mixed"} or bool(grok_plan.get("model")), str(grok_plan.get("model")))
        fallback_path = newest(grok_dir, "fallback-v*.json")
        add(checks, "grok_fallback_record", mode not in {"mixed", "ffmpeg_fallback"} or fallback_path is not None, str(fallback_path) if fallback_path else "无需回退")
        missing_outputs: list[str] = []
        invalid_qc: list[str] = []
        invalid_durations: list[str] = []
        invalid_parallel_triggers: list[str] = []
        if isinstance(selected, list):
            for shot in selected:
                estimated_start = as_float(shot.get("estimated_voice_start"))
                estimated_end = as_float(shot.get("estimated_voice_end"))
                raw_bucket = as_float(shot.get("raw_duration_bucket_seconds"))
                if (
                    estimated_start is None
                    or estimated_end is None
                    or estimated_end <= estimated_start
                    or raw_bucket not in {6.0, 10.0}
                    or parse_timestamp(shot.get("video_started_at_utc")) is None
                ):
                    invalid_parallel_triggers.append(str(shot.get("id")))
        if mode in {"grok_oauth", "mixed"} and isinstance(selected, list):
            for shot in selected:
                if shot.get("status") == "fallback":
                    continue
                output = project / str(shot.get("output", ""))
                qc_value = shot.get("qc") or str(shot.get("output", "")).replace("-final.mp4", "-qc.json")
                qc_path = project / str(qc_value)
                if not output.is_file() or not qc_path.is_file():
                    missing_outputs.append(str(shot.get("id")))
                    continue
                qc = read_json(qc_path)
                watermark_action = qc.get("watermark_action")
                if qc.get("status") not in {"approved", "fallback"}:
                    invalid_qc.append(str(shot.get("id")))
                if qc.get("watermark_detected") is True and watermark_action not in {"accepted", "fallback"}:
                    invalid_qc.append(str(shot.get("id")))
                if find_secret_fields(qc):
                    invalid_qc.append(str(shot.get("id")))
                target_clip_duration = as_float(shot.get("target_duration_seconds"))
                if target_clip_duration is None or target_clip_duration <= 0:
                    invalid_durations.append(str(shot.get("id")))
                else:
                    try:
                        actual_clip_duration = float(ffprobe(output).get("format", {}).get("duration", 0))
                        if abs(actual_clip_duration - target_clip_duration) > TIMING_TOLERANCE_SECONDS:
                            invalid_durations.append(str(shot.get("id")))
                    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError, ValueError):
                        invalid_durations.append(str(shot.get("id")))
        add(checks, "grok_outputs", not missing_outputs, f"缺失 {missing_outputs}" if missing_outputs else "素材已落盘或无需生成")
        add(checks, "grok_qc", not invalid_qc, f"不合格 {sorted(set(invalid_qc))}" if invalid_qc else "质检记录合法")
        add(checks, "grok_clip_duration", not invalid_durations, f"时长不匹配 {sorted(set(invalid_durations))}" if invalid_durations else "全部动态片段与口播区间同长")
        add(checks, "grok_parallel_trigger_metadata", not invalid_parallel_triggers, f"缺少并行触发字段 {sorted(set(invalid_parallel_triggers))}" if invalid_parallel_triggers else "全部镜头保留预估档位和视频启动时间")
        leaked = find_secret_fields(grok_plan)
        add(checks, "grok_plan_secret_free", not leaked, f"敏感字段 {leaked}" if leaked else "未落盘凭证")

    storyboard_path = newest(project / "07-分镜", "storyboard-v*.json")
    image_generation_path = newest(project / "07-分镜", "image-generation-v*.json")
    opening_path = newest(project / "10-片头字幕", "opening-v*.json")
    visual_locks = sorted((project / "08-正文画面").rglob("visual-lock-v*.png"))
    shots = sorted((project / "08-正文画面").rglob("shot-*.png"))
    image_record: dict[str, Any] = {}
    image_shots_by_output: dict[str, dict[str, Any]] = {}
    add(checks, "storyboard_file", storyboard_path is not None, str(storyboard_path) if storyboard_path else "未找到")
    if isinstance(image_generation, dict):
        add(checks, "image_generation_record", image_generation_path is not None, str(image_generation_path) if image_generation_path else "未找到")
        if image_generation_path:
            image_record = read_json(image_generation_path)
            outputs = image_record.get("outputs", [])
            visual_lock_value = str(image_record.get("visual_lock") or "")
            output_files_ok = (
                isinstance(outputs, list)
                and bool(outputs)
                and all(
                    is_within(project / str(item), project)
                    and (project / str(item)).is_file()
                    for item in outputs
                )
                and bool(visual_lock_value)
                and is_within(project / visual_lock_value, project)
                and (project / visual_lock_value).is_file()
            )
            image_record_ok = (
                image_record.get("provider") == image_generation.get("provider")
                and image_record.get("selection_mode") == image_generation.get("selection_mode")
                and image_record.get("generation_mode") == "parallel_individual"
                and image_record.get("batch_strategy") == "parallel_all"
                and image_record.get("pre_join_timing_basis") == "script_estimated"
                and image_record.get("timing_basis") == "voice_actual_after_join"
                and not find_secret_fields(image_record)
                and output_files_ok
            )
            add(checks, "image_generation_provider", image_record_ok, f"{image_record.get('provider')} / {len(outputs) if isinstance(outputs, list) else 0} 张")
            batch_plan_value = str(image_record.get("batch_plan") or "")
            batch_plan_path = project / batch_plan_value if batch_plan_value else None
            batch_plan: dict[str, Any] = {}
            batch_errors = ["batch_plan:path"]
            if batch_plan_path is not None and batch_plan_path.is_file():
                batch_plan = read_json(batch_plan_path)
                batch_errors = validate_parallel_image_batch(
                    batch_plan,
                    project,
                    str(image_record.get("provider") or ""),
                    {str(item) for item in outputs} if isinstance(outputs, list) else set(),
                )
            add(
                checks,
                "parallel_image_batch",
                not batch_errors,
                f"违规 {batch_errors}" if batch_errors else batch_plan_value,
            )
            shot_contract_errors, image_shots_by_output = validate_image_shot_contract(image_record.get("shots"), outputs)
            shot_files_ok = all(
                is_within(project / output, project) and (project / output).is_file()
                for output in image_shots_by_output
            )
            add(
                checks,
                "image_script_clear_emotion_wardrobe_contract",
                not shot_contract_errors and shot_files_ok,
                f"违规 {shot_contract_errors}" if shot_contract_errors else f"{len(image_shots_by_output)} 张均绑定文案情绪、清透成像、轻便服装、侧脸和风景",
            )
            primary_by_output = {
                str(item.get("output")): item
                for item in batch_plan.get("requests", [])
                if isinstance(item, dict) and item.get("role") == "body_shot"
            }
            retry_plan = batch_plan.get("retry_batch", {}) if isinstance(batch_plan, dict) else {}
            retry_by_output = {
                str(item.get("output")): item
                for item in retry_plan.get("requests", [])
                if isinstance(item, dict) and item.get("role") == "image_retry"
            } if isinstance(retry_plan, dict) else {}
            binding_errors: list[str] = []
            for output, shot in image_shots_by_output.items():
                if shot.get("source_type") == "direct_generation":
                    request = primary_by_output.get(output)
                    if (
                        not request
                        or shot.get("batch_id") != batch_plan.get("id")
                        or shot.get("request_id") != request.get("id")
                    ):
                        binding_errors.append(f"{output}:primary_batch_binding")
                elif shot.get("source_type") == "retry_generation":
                    request = retry_by_output.get(output)
                    if not request or shot.get("retry_batch_id") != retry_plan.get("id"):
                        binding_errors.append(f"{output}:retry_batch_binding")
            add(
                checks,
                "image_batch_bindings",
                not binding_errors,
                f"违规 {binding_errors}" if binding_errors else f"{len(image_shots_by_output)} 张均绑定并发请求",
            )
            if grok_plan:
                selected = grok_plan.get("selected_shots", [])
                selected_sources = {
                    str(item.get("source")) for item in selected if isinstance(item, dict)
                } if isinstance(selected, list) else set()
                expected_sources = {str(item) for item in outputs} if isinstance(outputs, list) else set()
                mode = grok_plan.get("mode")
                animation_coverage_ok = (
                    mode in {"grok_oauth", "mixed"}
                    and bool(expected_sources)
                    and selected_sources == expected_sources
                ) or mode == "ffmpeg_fallback"
                add(
                    checks,
                    "grok_animation_coverage",
                    animation_coverage_ok,
                    f"{len(selected_sources)} / {len(expected_sources)} 张；mode={mode}",
                )
                selected_by_source = {
                    str(item.get("source")): item for item in selected if isinstance(item, dict)
                } if isinstance(selected, list) else {}
                grok_binding_errors: list[str] = []
                for source, source_shot in image_shots_by_output.items():
                    planned = selected_by_source.get(source)
                    if not planned:
                        grok_binding_errors.append(f"{source}:missing")
                        continue
                    source_voice_start = as_float(source_shot.get("voice_start"))
                    source_voice_end = as_float(source_shot.get("voice_end"))
                    planned_voice_start = as_float(planned.get("voice_start"))
                    planned_voice_end = as_float(planned.get("voice_end"))
                    planned_duration = as_float(planned.get("target_duration_seconds"))
                    timing_values_ok = None not in {
                        source_voice_start,
                        source_voice_end,
                        planned_voice_start,
                        planned_voice_end,
                        planned_duration,
                    }
                    expected_duration = (
                        source_voice_end - source_voice_start
                        if source_voice_start is not None and source_voice_end is not None
                        else -1
                    )
                    binding_ok = (
                        timing_values_ok
                        and planned.get("script_segment_ids") == source_shot.get("script_segment_ids")
                        and str(planned.get("narration_text") or "").strip() == str(source_shot.get("narration_text") or "").strip()
                        and abs((planned_voice_start or 0) - (source_voice_start or 0)) <= TIMING_TOLERANCE_SECONDS
                        and abs((planned_voice_end or 0) - (source_voice_end or 0)) <= TIMING_TOLERANCE_SECONDS
                        and abs((planned_duration or 0) - expected_duration) <= TIMING_TOLERANCE_SECONDS
                    )
                    if not binding_ok:
                        grok_binding_errors.append(f"{source}:mismatch")
                add(
                    checks,
                    "grok_script_timing_binding",
                    not grok_binding_errors,
                    f"违规 {grok_binding_errors}" if grok_binding_errors else f"{len(image_shots_by_output)} 条动态计划继承文案时码",
                )
    add(checks, "visual_lock", bool(visual_locks), str(visual_locks[-1]) if visual_locks else "未找到")
    add(checks, "visual_shots", bool(shots), f"{len(shots)} 张")
    add(checks, "opening_file", opening_path is not None, str(opening_path) if opening_path else "未找到")
    opening_record: dict[str, Any] = {}
    if opening_path:
        opening_record = read_json(opening_path)
        validate_opening_contract(
            opening_record,
            project,
            checks,
            str(manifest.get("title", "")),
            content_contract_version,
        )
    visual_step = manifest.get("steps", {}).get("visual_package", {})
    visual_artifacts = visual_step.get("artifacts", [])
    visual_artifact_set = {str(item) for item in visual_artifacts}
    missing_visual_artifacts = [str(item) for item in visual_artifacts if not (project / str(item)).is_file()]
    if isinstance(image_generation, dict):
        image_record_registered = (
            image_generation_path is not None
            and str(image_generation_path.relative_to(project)) in {str(item) for item in visual_artifacts}
        )
        add(
            checks,
            "image_generation_artifact_registered",
            image_record_registered,
            str(image_generation_path.relative_to(project)) if image_generation_path else "未找到生图记录",
        )
    if opening_record:
        required_opening_artifacts = {
            str(opening_record.get("mask_source_video_asset", "")),
            str(opening_record.get("mask_source_plan_asset", "")),
            str(opening_record.get("masked_keyword_video_asset", "")),
            str(opening_path.relative_to(project)) if opening_path else "",
        }
        opening_artifacts_registered = "" not in required_opening_artifacts and required_opening_artifacts.issubset(visual_artifact_set)
        add(
            checks,
            "opening_mask_artifacts_registered",
            opening_artifacts_registered,
            str(sorted(required_opening_artifacts)),
        )
    add(
        checks,
        "visual_package_review_ready",
        visual_step.get("status") in {"awaiting_confirmation", "confirmed"},
        str(visual_step.get("status")),
    )
    add(
        checks,
        "visual_package_artifacts",
        len(visual_artifacts) >= 6 and not missing_visual_artifacts,
        f"缺失 {missing_visual_artifacts}" if missing_visual_artifacts else f"{len(visual_artifacts)} 个素材已落盘",
    )
    paired_status_ok = (
        sound_step.get("status") in {"awaiting_confirmation", "confirmed"}
        and visual_step.get("status") in {"awaiting_confirmation", "confirmed"}
    )
    add(checks, "sound_visual_paired_review", paired_status_ok, f"sound={sound_step.get('status')} / visual={visual_step.get('status')}")
    pipeline_path = newest(project / "07-分镜", "parallel-pipeline-v*.json")
    add(checks, "parallel_pipeline_file", pipeline_path is not None, str(pipeline_path) if pipeline_path else "未找到")
    pipeline_errors = validate_parallel_pipeline_run(
        read_json(pipeline_path) if pipeline_path else None,
        project,
        script_path,
        {str(shot.get("id") or "") for shot in image_shots_by_output.values()},
    )
    add(checks, "parallel_pipeline_execution", not pipeline_errors, f"违规 {pipeline_errors}" if pipeline_errors else "四分支并行、逐图触发和实际时码汇合证据完整")
    if args.stage == "visual_package":
        return finish(checks, args.stage)

    timeline_dir = project / "11-时间轴"
    timeline: dict[str, Any] = {}
    timeline_path = newest(timeline_dir, "timeline-v*.json")
    add(checks, "timeline_file", timeline_path is not None, str(timeline_path) if timeline_path else "未找到")
    if timeline_path:
        timeline = read_json(timeline_path)
        timeline_duration = as_float(timeline.get("duration"))
        locked_duration_value = as_float(duration_locked)
        timeline_duration_ok = (
            timeline_duration is not None
            and locked_duration_value is not None
            and abs(timeline_duration - locked_duration_value) <= TIMING_TOLERANCE_SECONDS
        )
        add(checks, "timeline_locked_duration", timeline_duration_ok, f"时间轴 {timeline_duration} / 配音锁定 {locked_duration_value}")
        expected_timing_source = str(timing_path.relative_to(project)) if timing_path else ""
        timing_source_ok = (
            timeline.get("duration_source") == "manifest.duration.locked"
            and timeline.get("voice_timing_source") == expected_timing_source
        )
        add(checks, "timeline_duration_source", timing_source_ok, f"{timeline.get('duration_source')} / {timeline.get('voice_timing_source')}")
        add(checks, "delivery", timeline.get("delivery") == "jianying_draft", str(timeline.get("delivery")))
        add(
            checks,
            "timeline_delivery_profile",
            timeline.get("deliveryProfile") == DEFAULT_DELIVERY["profile"],
            str(timeline.get("deliveryProfile")),
        )
        add(checks, "preview_renderer", timeline.get("preview_renderer") in {None, "ffmpeg"}, str(timeline.get("preview_renderer")))
        tl_canvas = timeline.get("canvas", {})
        add(
            checks,
            "timeline_canvas",
            (tl_canvas.get("width"), tl_canvas.get("height"), tl_canvas.get("fps")) == (1080, 1440, 30),
            f"{tl_canvas.get('width')}x{tl_canvas.get('height')}@{tl_canvas.get('fps')}",
        )
        if isinstance(typography, dict):
            timeline_typography = timeline.get("typography", {})
            timeline_typography_ok = (
                timeline_typography.get("chinese_font_id") == DEFAULT_CHINESE_FONT_ID
                and timeline_typography.get("chinese_font_asset") == DEFAULT_CHINESE_FONT_ASSET
                and timeline_typography.get("title_px") == 88
                and timeline_typography.get("author_px") == 44
                and timeline_typography.get("zh_caption_px") == 60
                and timeline_typography.get("english_font_family") == "Georgia"
                and timeline_typography.get("en_caption_px") == 32
            )
            add(checks, "timeline_typography", timeline_typography_ok, str(timeline_typography))
        opening = timeline.get("opening", {})
        book_meta = timeline.get("bookMeta", {})
        validate_opening_contract(
            opening,
            project,
            checks,
            str(book_meta.get("title", "")),
            content_contract_version,
        )

        opening_assets = timeline.get("openingTrack", [])
        opening_assets_ok = bool(opening_assets) and all(
            (project / str(item.get("asset", ""))).is_file() for item in opening_assets
        )
        add(checks, "opening_track", opening_assets_ok, f"{len(opening_assets)} 个可编辑片头素材")
        opening_ids = {str(item.get("id", "")) for item in opening_assets}
        carousel_track_items = [item for item in opening_assets if str(item.get("id", "")).startswith("carousel-")]
        expected_carousel_track_count = (
            int(opening.get("carousel_count") or len(opening.get("carousel_cards", [])))
            if content_contract_version >= 4 or bool(str(opening.get("carousel_plan_asset") or ""))
            else 9
        )
        opening_structure_ok = {"target-flash", "masked-keyword", "target-cover-hold", "target-cover-waterwave-page", "target-lock"}.issubset(opening_ids) and len(carousel_track_items) == expected_carousel_track_count
        add(checks, "opening_track_structure", opening_structure_ok, f"{len(carousel_track_items)} 张轮播卡 / IDs {sorted(opening_ids)}")
        target_lock_items = [item for item in opening_assets if item.get("id") == "target-lock"]
        waterdrop_effect_items = [item for item in opening_assets if item.get("id") == "target-cover-waterwave-page"]
        masked_keyword_items = [item for item in opening_assets if item.get("id") == "masked-keyword"]
        video_suffixes = {".mp4", ".mov", ".m4v", ".webm"}
        target_cover_title_page = str(opening.get("target_cover_title_page_asset") or "")
        target_hero_lock_ok = (
            len(target_lock_items) == 1
            and str(target_lock_items[0].get("asset") or "") == target_cover_title_page
            and target_lock_items[0].get("cover_visible_while_title_spoken") is True
            and abs(float(target_lock_items[0].get("end", -9)) - float(opening.get("body_voice_start", 9))) <= TIMING_TOLERANCE_SECONDS
        )
        masked_keyword_video_ok = len(masked_keyword_items) == 1 and Path(str(masked_keyword_items[0].get("asset", ""))).suffix.lower() in video_suffixes
        add(checks, "target_cover_lock_asset", target_hero_lock_ok, str(target_lock_items[0].get("asset")) if target_lock_items else "缺失")
        add(checks, "masked_keyword_video", masked_keyword_video_ok, str(masked_keyword_items[0].get("asset")) if masked_keyword_items else "缺失")
        opening_water = opening.get("waterdrop_lock_response", {})
        waterdrop_track_ok = (
            len(waterdrop_effect_items) == 1
            and waterdrop_effect_items[0].get("layer") == "page_effect"
            and waterdrop_effect_items[0].get("effect_on") == "entire_page"
            and Path(str(waterdrop_effect_items[0].get("asset", ""))).suffix.lower() == ".mp4"
            and abs(float(waterdrop_effect_items[0].get("start", -9)) - float(opening_water.get("visual_start", 9))) <= (1 / 30 + 0.001)
            and abs(float(waterdrop_effect_items[0].get("end", -9)) - float(opening_water.get("visual_end", 9))) <= (1 / 30 + 0.001)
            and waterdrop_effect_items[0].get("motion", {}).get("type") == "full_frame_displacement_map"
            and waterdrop_effect_items[0].get("motion", {}).get("page_deformation") is True
            and waterdrop_effect_items[0].get("motion", {}).get("overlay_graphic") is False
            and waterdrop_effect_items[0].get("motion", {}).get("visible_ring") is False
            and abs(float(waterdrop_effect_items[0].get("wave_trigger_at", -9)) - float(opening_water.get("wave_trigger_at", 9))) <= (1 / 30 + 0.001)
        )
        add(checks, "waterwave_full_page_track", waterdrop_track_ok, str(waterdrop_effect_items[0]) if waterdrop_effect_items else "缺失")

        audio_items = timeline.get("audioTrack", [])
        audio_types = {str(item.get("type", "")) for item in audio_items}
        audio_assets_ok = all((project / str(item.get("asset", ""))).is_file() for item in audio_items)
        add(checks, "audio_tracks", {"voice", "bgm"}.issubset(audio_types), str(sorted(audio_types)))
        add(checks, "audio_assets", bool(audio_items) and audio_assets_ok, f"{len(audio_items)} 个音频素材")
        voice_items = [item for item in audio_items if item.get("type") == "voice"]
        voice_track_locked = (
            len(voice_items) == 1
            and as_float(voice_items[0].get("start")) is not None
            and abs(float(voice_items[0].get("start")) - 0.0) <= TIMING_TOLERANCE_SECONDS
            and locked_duration_value is not None
            and as_float(voice_items[0].get("end")) is not None
            and abs(float(voice_items[0].get("end")) - locked_duration_value) <= TIMING_TOLERANCE_SECONDS
        )
        add(checks, "voice_track_locked_duration", voice_track_locked, str(voice_items[0]) if voice_items else "缺失")
        waterdrop_audio_items = [item for item in audio_items if item.get("type") == "sfx" and "waterdrop" in str(item.get("id", ""))]
        waterdrop_audio_ok = (
            len(waterdrop_audio_items) == 1
            and abs(float(waterdrop_audio_items[0].get("start", -9)) - float(opening_water.get("wave_trigger_at", 9))) <= (1 / 30 + 0.001)
        )
        add(checks, "waterwave_audio_trigger_sync", waterdrop_audio_ok, str(waterdrop_audio_items[0]) if waterdrop_audio_items else "缺失")
        book_meta_ok = bool(str(book_meta.get("title", "")).strip()) and bool(str(book_meta.get("author", "")).strip())
        add(checks, "book_meta", book_meta_ok, f"{book_meta.get('title', '')} / {book_meta.get('author', '')}")

        scenes = timeline.get("sceneTrack", [])
        scene_coverage_errors = validate_scene_voice_coverage(scenes, opening.get("body_voice_start"), duration_locked)
        add(
            checks,
            "scene_voice_coverage",
            not scene_coverage_errors,
            f"违规 {scene_coverage_errors}" if scene_coverage_errors else "正文口播从片头后无缝覆盖到配音终点",
        )
        scene_binding_errors: list[str] = []
        for scene in scenes if isinstance(scenes, list) else []:
            source_still = str(scene.get("source_still") or "")
            source_shot = image_shots_by_output.get(source_still)
            if not source_shot:
                scene_binding_errors.append(f"{scene.get('id')}:source_still")
                continue
            scene_voice_start = as_float(scene.get("voice_start"))
            scene_voice_end = as_float(scene.get("voice_end"))
            source_voice_start = as_float(source_shot.get("voice_start"))
            source_voice_end = as_float(source_shot.get("voice_end"))
            timing_values_ok = None not in {
                scene_voice_start,
                scene_voice_end,
                source_voice_start,
                source_voice_end,
            }
            binding_ok = (
                timing_values_ok
                and scene.get("script_segment_ids") == source_shot.get("script_segment_ids")
                and str(scene.get("narration_text") or "").strip() == str(source_shot.get("narration_text") or "").strip()
                and abs((scene_voice_start or 0) - (source_voice_start or 0)) <= TIMING_TOLERANCE_SECONDS
                and abs((scene_voice_end or 0) - (source_voice_end or 0)) <= TIMING_TOLERANCE_SECONDS
            )
            if not binding_ok:
                scene_binding_errors.append(f"{scene.get('id')}:binding")
        add(
            checks,
            "scene_script_image_binding",
            not scene_binding_errors and bool(scenes),
            f"违规 {scene_binding_errors}" if scene_binding_errors else f"{len(scenes)} 组场景继承生图文案时码",
        )
        shot_lengths = [float(s["end"]) - float(s["start"]) for s in scenes if "start" in s and "end" in s]
        target_duration = float(timeline.get("duration") or duration_locked or duration_estimated or duration_requested or 0)
        body_span = sum(shot_lengths)
        average = body_span / len(shot_lengths) if shot_lengths else 0
        count_ok = bool(shot_lengths) and 5.0 <= average <= 14.0
        add(checks, "scene_track", count_ok, f"{len(shot_lengths)} 组，平均 {average:.2f} 秒")
        if shot_lengths:
            median = statistics.median(shot_lengths)
            add(checks, "shot_median", 4.0 <= median <= 14.0, f"中位数 {median:.2f} 秒")

        allowed_change_reasons = {
            "initial_state",
            "subject_relation_change",
            "psychological_state_change",
            "narrative_space_change",
            "symbol_change",
            "causal_stage_change",
            "action_release",
        }
        invalid_scene_logic = []
        for index, scene in enumerate(scenes):
            reason = scene.get("visual_change_reason")
            stage = str(scene.get("emotional_stage", "")).strip()
            reason_ok = reason == "initial_state" if index == 0 else reason in allowed_change_reasons - {"initial_state"}
            if not stage or not reason_ok:
                invalid_scene_logic.append(scene.get("id"))
        add(
            checks,
            "scene_semantic_logic",
            not invalid_scene_logic,
            f"违规镜头 {invalid_scene_logic}" if invalid_scene_logic else f"{len(scenes)} 组均有心理阶段和换图理由",
        )

        deterministic_motion = {"zoom_in", "zoom_out", "pan_left", "pan_right", "emotional_hold"}
        allowed_motion = deterministic_motion | {"grok_video", "ltx_video"}
        invalid_motion = []
        repeated_motion = []
        previous_deterministic: str | None = None
        deterministic_count = 0
        grok_scene_count = 0
        for scene in scenes:
            motion = scene.get("motion", {})
            motion_type = motion.get("type")
            scale_start = float(motion.get("scale_start", 1))
            scale_end = float(motion.get("scale_end", 1))
            scale_delta = abs(scale_end - scale_start)
            pan_x_ratio = float(motion.get("pan_x_ratio", 0))
            pan_y_ratio = float(motion.get("pan_y_ratio", 0))
            container = motion.get("container", {})
            container_ok = (
                isinstance(container, dict)
                and container.get("coverage") == "full_canvas"
                and container.get("overflow") == "hidden"
                and container.get("fit") == "cover"
                and container.get("transform_target") == "inner_image"
            )
            common_static_ok = (
                motion.get("interpolation") == "cubic_ease_in_out"
                and motion.get("sample_per_frame") is True
                and container_ok
            )
            if motion_type in deterministic_motion:
                deterministic_count += 1
                if previous_deterministic == motion_type:
                    repeated_motion.append(scene.get("id"))
                previous_deterministic = str(motion_type)
            else:
                previous_deterministic = None
            if motion_type in {"grok_video", "ltx_video"}:
                grok_scene_count += 1
            type_values_ok = (
                (
                    motion_type == "zoom_in"
                    and scale_start == 1.0
                    and 1.10 <= scale_end <= 1.13
                    and abs(pan_x_ratio) <= 0.0001
                    and abs(pan_y_ratio) <= 0.0001
                    and common_static_ok
                )
                or (
                    motion_type == "zoom_out"
                    and 1.10 <= scale_start <= 1.13
                    and scale_end == 1.0
                    and abs(pan_x_ratio) <= 0.0001
                    and abs(pan_y_ratio) <= 0.0001
                    and common_static_ok
                )
                or (
                    motion_type == "pan_left"
                    and 1.08 <= scale_start <= 1.13
                    and 1.08 <= scale_end <= 1.13
                    and scale_delta <= 0.005
                    and -0.04 <= pan_x_ratio <= -0.01
                    and abs(pan_y_ratio) <= 0.0001
                    and common_static_ok
                )
                or (
                    motion_type == "pan_right"
                    and 1.08 <= scale_start <= 1.13
                    and 1.08 <= scale_end <= 1.13
                    and scale_delta <= 0.005
                    and 0.01 <= pan_x_ratio <= 0.04
                    and abs(pan_y_ratio) <= 0.0001
                    and common_static_ok
                )
                or (
                    motion_type == "emotional_hold"
                    and scale_start == 1.0
                    and 1.02 <= scale_end <= 1.03
                    and abs(scale_end - 1.025) <= 0.005
                    and abs(pan_x_ratio) <= 0.0001
                    and abs(pan_y_ratio) <= 0.0001
                    and common_static_ok
                )
                or (
                    motion_type in {"grok_video", "ltx_video"}
                    and scale_delta == 0
                    and abs(pan_x_ratio) <= 0.0001
                    and abs(pan_y_ratio) <= 0.0001
                )
            )
            if (
                motion_type not in allowed_motion
                or not type_values_ok
            ):
                invalid_motion.append(scene.get("id"))
        add(checks, "micro_motion", not invalid_motion, f"违规镜头 {invalid_motion}" if invalid_motion else f"{len(scenes)} 组")
        add(
            checks,
            "motion_alternation",
            not repeated_motion,
            f"连续重复 {repeated_motion}" if repeated_motion else "相邻确定性镜头运动不重复",
        )
        add(
            checks,
            "motion_scene_coverage",
            deterministic_count + grok_scene_count == len(scenes),
            f"确定性 {deterministic_count} + Grok {grok_scene_count} / {len(scenes)}",
        )
        grok_assets_ok = all(
            str(scene.get("asset", "")).startswith("09-Grok视频/")
            for scene in scenes
            if scene.get("motion", {}).get("type") == "grok_video"
        )
        add(checks, "grok_scene_assets", grok_assets_ok, "Grok 片段路径合法" if grok_assets_ok else "Grok 片段必须位于 09-Grok视频")
        grok_files_exist = all(
            (project / str(scene.get("asset", ""))).is_file()
            for scene in scenes
            if scene.get("motion", {}).get("type") == "grok_video"
        )
        add(checks, "grok_scene_files", grok_files_exist, "Grok 片段已落盘" if grok_files_exist else "时间轴引用的 Grok 片段缺失")
        add(checks, "no_static_body_scene", deterministic_count + grok_scene_count == len(scenes), f"{len(scenes)} 个镜头全部有运动")

        subtitles = timeline.get("captionTrack", [])
        hook_start = as_float(opening.get("hook_start"))
        expand_end = as_float(opening.get("expand_end"))
        opening_caption_source = list(subtitles)
        if not any(
            as_float(item.get("end")) is not None
            and hook_start is not None
            and float(item["end"]) > hook_start
            and expand_end is not None
            and float(item.get("start", 999)) < expand_end
            for item in opening_caption_source
        ) and opening.get("mask_narration_captions_present") is True:
            opening_caption_source.extend(opening.get("mask_caption_track", []))
        opening_caption_intervals = sorted(
            (
                float(item["start"]),
                float(item["end"]),
            )
            for item in opening_caption_source
            if as_float(item.get("start")) is not None
            and as_float(item.get("end")) is not None
            and hook_start is not None
            and expand_end is not None
            and float(item["end"]) > hook_start
            and float(item["start"]) < expand_end
        )
        opening_caption_coverage_ok = bool(opening_caption_intervals)
        coverage_cursor = hook_start
        coverage_target = expand_end
        mask_caption_ends = [
            as_float(item.get("end"))
            for item in opening.get("mask_caption_track", [])
            if as_float(item.get("end")) is not None
        ]
        if coverage_target is not None and mask_caption_ends:
            coverage_target = min(coverage_target, max(mask_caption_ends))
        if opening_caption_coverage_ok and coverage_cursor is not None and expand_end is not None:
            for interval_start, interval_end in opening_caption_intervals:
                if interval_start > coverage_cursor + TIMING_TOLERANCE_SECONDS:
                    opening_caption_coverage_ok = False
                    break
                coverage_cursor = max(coverage_cursor, interval_end)
            opening_caption_coverage_ok = opening_caption_coverage_ok and coverage_target is not None and coverage_cursor >= coverage_target - TIMING_TOLERANCE_SECONDS
        add(
            checks,
            "opening_caption_coverage",
            opening_caption_coverage_ok,
            f"{hook_start}–{expand_end}s / {opening_caption_intervals}",
        )
        invalid = [(s.get("id"), han_count(s.get("zh", ""))) for s in subtitles if not 1 <= han_count(s.get("zh", "")) <= 16]
        add(checks, "subtitle_length", not invalid, f"超限 {invalid}" if invalid else f"{len(subtitles)} 张字幕")
        progressive = [s.get("id") for s in subtitles if abs(float(s.get("reveal_end", s.get("start", 0))) - float(s.get("start", 0))) > 0.001 or s.get("display_mode", "segment") != "segment"]
        add(checks, "subtitle_segment_display", not progressive, f"违规字幕 {progressive}" if progressive else "全部整段直接显示")
        add(checks, "caption_scene_decoupled", len(subtitles) > len(scenes), f"{len(subtitles)} 张字幕 / {len(scenes)} 组场景")
        add(checks, "accent_track_schema", isinstance(timeline.get("accentTrack"), list), f"{len(timeline.get('accentTrack', [])) if isinstance(timeline.get('accentTrack'), list) else 0} 条")
        transitions = timeline.get("transitionTrack", [])
        invalid_transitions = []
        transition_types: list[str] = []
        if isinstance(transitions, list):
            for transition in transitions:
                transition_id = f"{transition.get('from')}→{transition.get('to')}"
                transition_type = str(transition.get("type") or "")
                reason = str(transition.get("reason") or "")
                start = as_float(transition.get("start"))
                end = as_float(transition.get("end"))
                duration = as_float(transition.get("duration"))
                if duration is None and None not in {start, end}:
                    assert start is not None and end is not None
                    duration = end - start
                transition_types.append(transition_type)
                valid = (
                    transition_type == "hard_cut"
                    and reason in {"memory_fragment", "strong_turn"}
                    and duration is not None
                    and 0 <= duration <= (1 / 30 + 0.001)
                ) or (
                    transition_type == "short_fade"
                    and reason == "emotional_continuity"
                    and duration is not None
                    and 0.12 <= duration <= 0.30
                )
                if not valid:
                    invalid_transitions.append(transition_id)
        expected_transition_count = max(0, len(scenes) - 1)
        transition_count = len(transitions) if isinstance(transitions, list) else 0
        transition_count_ok = isinstance(transitions, list) and transition_count == expected_transition_count
        transition_variety_ok = transition_count < 3 or len(set(transition_types)) > 1
        add(
            checks,
            "transition_track",
            transition_count_ok and not invalid_transitions and transition_variety_ok,
            (
                f"数量 {transition_count if isinstance(transitions, list) else '非数组'}/{expected_transition_count}；"
                f"违规 {invalid_transitions}；类型 {transition_types}"
            ),
        )

        body_video_assets = sorted(str(path) for path in (project / "08-正文画面").rglob("*.mp4"))
        add(checks, "no_body_videos", not body_video_assets, f"违规素材 {body_video_assets}" if body_video_assets else "08-正文画面只有静态图")

    timeline_step = manifest.get("steps", {}).get("timeline_package", {})
    timeline_artifacts = timeline_step.get("artifacts", [])
    missing_timeline_artifacts = [str(item) for item in timeline_artifacts if not (project / str(item)).is_file()]
    add(
        checks,
        "timeline_package_review_ready",
        timeline_step.get("status") in {"awaiting_confirmation", "confirmed"},
        str(timeline_step.get("status")),
    )
    add(
        checks,
        "timeline_package_artifacts",
        len(timeline_artifacts) >= 4 and not missing_timeline_artifacts,
        f"缺失 {missing_timeline_artifacts}" if missing_timeline_artifacts else f"{len(timeline_artifacts)} 个素材已落盘",
    )
    if args.stage == "timeline_package" and args.video is None:
        preview_path = newest(project / "12-预览", "*.mp4")
        add(checks, "timeline_preview", preview_path is not None, str(preview_path) if preview_path else "未找到")
        if preview_path is not None:
            args.video = preview_path

    if args.draft and args.video is None:
        final_video_path = newest(project / "12-预览", "final-video-*.mp4")
        add(checks, "final_video_delivery", final_video_path is not None, str(final_video_path) if final_video_path else "未找到最终视频")
        if final_video_path is not None:
            args.video = final_video_path
    elif args.draft and args.video is not None:
        add(checks, "final_video_delivery", args.video.is_file(), str(args.video))

    if args.stage == "final_video" and args.video is None:
        final_video_path = newest(project / "12-预览", "final-video-*.mp4")
        add(checks, "final_video_delivery", final_video_path is not None, str(final_video_path) if final_video_path else "未找到最终视频")
        if final_video_path is not None:
            args.video = final_video_path

    if args.video:
        try:
            media = ffprobe(args.video.resolve())
            streams = media.get("streams", [])
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
            duration = float(media.get("format", {}).get("duration", 0))
            add(checks, "video_size", (video_stream.get("width"), video_stream.get("height")) == (1080, 1440), f"{video_stream.get('width')}x{video_stream.get('height')}")
            fps = frame_rate(video_stream.get("avg_frame_rate"))
            add(checks, "video_fps", fps is not None and abs(fps - 30.0) <= 0.001, f"{fps} fps")
            add(
                checks,
                "video_codec_profile",
                video_stream.get("codec_name") == "h264" and video_stream.get("pix_fmt") == "yuv420p",
                f"{video_stream.get('codec_name')} / {video_stream.get('pix_fmt')}",
            )
            timeline_duration = timeline.get("duration") if timeline_path else None
            target_duration = float(duration_locked or timeline_duration or 0)
            add(checks, "duration_locked", duration_locked is not None, str(duration_locked))
            add(checks, "video_duration", duration > 0 and target_duration > 0 and abs(duration - target_duration) <= TIMING_TOLERANCE_SECONDS, f"{duration:.3f} 秒，锁定 {target_duration:.3f} 秒")
            add(checks, "audio_track", audio_stream is not None, "存在" if audio_stream else "缺失")
            if audio_stream:
                add(
                    checks,
                    "audio_delivery_profile",
                    audio_stream.get("codec_name") == "aac"
                    and str(audio_stream.get("sample_rate")) == "48000"
                    and int(audio_stream.get("channels") or 0) == 2,
                    f"{audio_stream.get('codec_name')} / {audio_stream.get('sample_rate')} Hz / {audio_stream.get('channels')} ch",
                )
                levels = loudness(args.video.resolve())
                add(checks, "audio_lufs", -10.5 <= levels["lufs"] <= -9.5, f"{levels['lufs']:.2f} LUFS")
                add(checks, "audio_lra", 1.8 <= levels["lra"] <= 4.0, f"{levels['lra']:.2f} LU")
                add(checks, "audio_true_peak", levels["true_peak"] <= -1.0, f"{levels['true_peak']:.2f} dBTP")
        except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as exc:
            add(checks, "ffprobe", False, str(exc))

        if args.stage == "final_video" or args.video.name.startswith("final-video-"):
            final_video_step = manifest.get("steps", {}).get("final_video", {})
            add(
                checks,
                "final_video_review_ready",
                final_video_step.get("status") in {"awaiting_confirmation", "confirmed"},
                str(final_video_step.get("status")),
            )

    if args.draft:
        draft_path = args.draft.expanduser().resolve()
        content_path = draft_path / "draft_content.json"
        meta_path = draft_path / "draft_meta_info.json"
        report_path = draft_path / "book_emotion_draft_report.json"
        entry_ok = (draft_path / "draft_info.json").is_file() or any((draft_path / "Timelines").glob("*/draft_info.json"))
        add(checks, "jianying_draft_dir", draft_path.is_dir(), str(draft_path))
        add(checks, "jianying_content", content_path.is_file(), str(content_path))
        add(checks, "jianying_meta", meta_path.is_file(), str(meta_path))
        add(checks, "jianying_entry", entry_ok, "入口文件存在" if entry_ok else "缺少剪映入口文件")
        add(checks, "jianying_report", report_path.is_file(), str(report_path))
        media_dir = draft_path / "Resources" / "local_media"
        localized = [path for path in media_dir.glob("*") if path.is_file()] if media_dir.is_dir() else []
        add(checks, "jianying_local_media", bool(localized), f"{len(localized)} 个媒体")
        draft_report: dict[str, Any] = {}
        if report_path.is_file():
            draft_report = read_json(report_path)
            report_timeline = Path(str(draft_report.get("timeline") or "")).expanduser()
            report_video = Path(str(draft_report.get("video_master") or "")).expanduser()
            same_timeline_ok = (
                draft_report.get("same_timeline_as_video_master") is True
                and timeline_path is not None
                and report_timeline.is_file()
                and report_timeline.resolve() == timeline_path.resolve()
            )
            expected_video = args.video.expanduser().resolve() if args.video else None
            editable_delivery_ok = (
                draft_report.get("delivery_profile") == DEFAULT_DELIVERY["profile"]
                and draft_report.get("flattened_final_mp4") is False
                and report_video.is_file()
                and expected_video is not None
                and report_video.resolve() == expected_video
            )
            add(checks, "jianying_same_timeline_master", same_timeline_ok, str(report_timeline))
            add(checks, "jianying_editable_delivery", editable_delivery_ok, str(report_video))
        if isinstance(typography, dict):
            localized_font = draft_path / "Resources" / "local_fonts" / "杨任东竹石体-Heavy.ttf"
            font_packaged = (
                localized_font.is_file()
                and sha256(localized_font) == DEFAULT_CHINESE_FONT_SHA256
            )
            add(checks, "jianying_local_font", font_packaged, str(localized_font))
            if report_path.is_file():
                binding_reported = (
                    draft_report.get("font_binding") == "requires_jianying_local_font_activation"
                    and draft_report.get("typography", {}).get("chinese_font_id") == DEFAULT_CHINESE_FONT_ID
                )
                add(checks, "jianying_font_binding_report", binding_reported, str(draft_report.get("font_binding")))
        if content_path.is_file():
            content = read_json(content_path)
            track_names = {str(track.get("name") or track.get("attribute") or "") for track in content.get("tracks", [])}
            required_tracks = {"body_visual_a", "voice", "bgm", "zh_captions", "en_captions"}
            missing_tracks = sorted(required_tracks - track_names)
            add(checks, "jianying_tracks", not missing_tracks, f"缺少 {missing_tracks}" if missing_tracks else f"{len(track_names)} 条轨道")

        draft_step = manifest.get("steps", {}).get("jianying_draft", {})
        add(
            checks,
            "jianying_draft_review_ready",
            draft_step.get("status") in {"awaiting_confirmation", "confirmed"},
            str(draft_step.get("status")),
        )

    if args.stage == "timeline_package":
        return finish(checks, args.stage)

    return finish(checks, args.stage)


if __name__ == "__main__":
    raise SystemExit(main())

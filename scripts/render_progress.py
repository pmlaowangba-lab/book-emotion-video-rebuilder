#!/usr/bin/env python3
"""从事件驱动生产记录生成机器可读和人类可读的实时进度快照。"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TERMINAL = {"completed", "fallback"}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("pipeline 必须是 JSON 对象")
    return value


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def task_shot_id(task_id: str) -> str | None:
    prefix = task_id.split(".", 1)[0]
    return prefix if prefix.startswith("shot-") else None


def build_snapshot(pipeline: dict[str, Any], pipeline_path: Path) -> dict[str, Any]:
    tasks = pipeline.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("pipeline.tasks 必须是数组")
    normalized = [item for item in tasks if isinstance(item, dict) and str(item.get("id") or "")]
    task_map = {str(item["id"]): item for item in normalized}
    counts = Counter(str(item.get("status") or "pending") for item in normalized)
    total = len(normalized)
    finished = sum(counts[item] for item in TERMINAL)

    groups: dict[str, Counter[str]] = defaultdict(Counter)
    shots: dict[str, dict[str, str]] = defaultdict(dict)
    running: list[str] = []
    blocked: list[str] = []
    ready: list[str] = []
    waiting: list[dict[str, Any]] = []
    recent: list[tuple[str, str]] = []

    for item in normalized:
        task_id = str(item["id"])
        status = str(item.get("status") or "pending")
        group = str(item.get("resource_group") or "other")
        groups[group][status] += 1
        shot_id = task_shot_id(task_id)
        if shot_id:
            shots[shot_id][task_id.removeprefix(f"{shot_id}.")] = status
        if status == "running":
            running.append(task_id)
        if status == "blocked":
            blocked.append(task_id)
        completed_at = str(item.get("completed_at_utc") or "")
        if completed_at and status in TERMINAL:
            recent.append((completed_at, task_id))
        if status == "pending":
            dependencies = [str(value) for value in item.get("depends_on", [])]
            missing = [
                value
                for value in dependencies
                if str(task_map.get(value, {}).get("status") or "pending") not in TERMINAL
            ]
            if missing:
                waiting.append({"task": task_id, "waiting_for": missing})
            else:
                ready.append(task_id)

    join_status = str((pipeline.get("join") or {}).get("status") or "pending")
    phase = "completed" if join_status == "completed" and finished == total else "production"
    if blocked:
        phase = "blocked"
    return {
        "schema_version": 1,
        "source_pipeline": str(pipeline_path),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "overall": {
            "percent": round((finished / total * 100) if total else 0, 1),
            "total": total,
            "finished": finished,
            "running": counts["running"],
            "pending": counts["pending"],
            "blocked": counts["blocked"],
            "fallback": counts["fallback"],
        },
        "resource_groups": {
            group: {
                "total": sum(statuses.values()),
                "finished": sum(statuses[item] for item in TERMINAL),
                "running": statuses["running"],
                "pending": statuses["pending"],
                "blocked": statuses["blocked"],
            }
            for group, statuses in sorted(groups.items())
        },
        "shots": dict(sorted(shots.items())),
        "running_tasks": sorted(running),
        "ready_tasks": sorted(ready),
        "waiting_tasks": waiting,
        "blocked_tasks": sorted(blocked),
        "recently_finished": [item[1] for item in sorted(recent, reverse=True)[:5]],
    }


def render_markdown(snapshot: dict[str, Any]) -> str:
    overall = snapshot["overall"]
    lines = [
        "# 实时生产进度",
        "",
        f"- 阶段：`{snapshot['phase']}`",
        f"- 总进度：**{overall['percent']}%**（{overall['finished']}/{overall['total']}）",
        f"- 运行中：{overall['running']}；待执行：{overall['pending']}；阻塞：{overall['blocked']}；回退：{overall['fallback']}",
        f"- 更新时间：`{snapshot['updated_at_utc']}`",
        "",
        "## 资源组",
        "",
        "| 资源组 | 完成 | 运行中 | 待执行 | 阻塞 |",
        "|---|---:|---:|---:|---:|",
    ]
    for group, values in snapshot["resource_groups"].items():
        lines.append(
            f"| {group} | {values['finished']}/{values['total']} | {values['running']} | {values['pending']} | {values['blocked']} |"
        )
    lines.extend(["", "## 镜头进度", ""])
    for shot_id, values in snapshot["shots"].items():
        stages = " → ".join(f"{name}:{status}" for name, status in values.items())
        lines.append(f"- `{shot_id}`：{stages}")
    lines.extend([
        "",
        "## 当前执行",
        "",
        f"- 运行中：{', '.join(snapshot['running_tasks']) or '无'}",
        f"- 已就绪：{', '.join(snapshot['ready_tasks']) or '无'}",
        f"- 最近完成：{', '.join(snapshot['recently_finished']) or '无'}",
        f"- 阻塞：{', '.join(snapshot['blocked_tasks']) or '无'}",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染事件驱动视频生产实时进度")
    parser.add_argument("--pipeline", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--markdown-output", required=True, type=Path)
    args = parser.parse_args()

    pipeline_path = args.pipeline.expanduser().resolve()
    snapshot = build_snapshot(read_json(pipeline_path), pipeline_path)
    atomic_write(args.json_output.expanduser().resolve(), json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    atomic_write(args.markdown_output.expanduser().resolve(), render_markdown(snapshot))
    print(args.json_output.expanduser().resolve())
    print(args.markdown_output.expanduser().resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""检查情绪读书视频 Skill 在当前电脑上的运行条件。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def result(name: str, state: str, detail: str) -> dict[str, str]:
    return {"name": name, "state": state, "detail": detail}


def model_index_complete(index_path: Path) -> bool:
    if not index_path.is_file():
        return False
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    shards = set(index.get("weight_map", {}).values())
    return bool(shards) and all((index_path.parent / shard).is_file() for shard in shards)


def main() -> int:
    checks: list[dict[str, str]] = []
    checks.append(result("Python", "ok" if sys.version_info >= (3, 9) else "missing", sys.version.split()[0]))

    for command in ("ffmpeg", "ffprobe", "git"):
        path = shutil.which(command)
        checks.append(result(command, "ok" if path else "missing", path or "未安装"))

    for module in ("numpy", "cv2", "PIL", "requests"):
        available = importlib.util.find_spec(module) is not None
        checks.append(result(f"python:{module}", "ok" if available else "missing", "已安装" if available else "pip install -r requirements.txt"))

    font = ROOT / "assets/fonts/杨任东竹石体-Heavy.ttf"
    checks.append(result("中文字体", "ok" if font.is_file() else "missing", str(font)))

    library_path = ROOT / "assets/opening-mask-video-library/manifest.json"
    try:
        library = json.loads(library_path.read_text(encoding="utf-8"))
        asset_id = library["default_asset_id"]
        entry = next(item for item in library["assets"] if item["id"] == asset_id)
        video = library_path.parent / entry["file"]
        actual_hash = hashlib.sha256(video.read_bytes()).hexdigest() if video.is_file() else ""
        expected_hash = entry["normalized_media"]["sha256"]
        ok = video.is_file() and actual_hash == expected_hash
        checks.append(result("片头飞鸟视频", "ok" if ok else "missing", str(video)))
    except Exception as exc:
        checks.append(result("片头飞鸟视频", "missing", str(exc)))

    env_file = ROOT / "assets/volcengine.env"
    has_api_key = False
    if env_file.is_file():
        has_api_key = any(
            line.startswith("VOLCENGINE_API_KEY=") and line.partition("=")[2].strip()
            for line in env_file.read_text(encoding="utf-8").splitlines()
        )
    checks.append(result("火山 TTS 凭证", "ok" if has_api_key else "optional_missing", "assets/volcengine.env"))

    bgm_manifest = ROOT / "assets/bgm-library/library.json"
    missing_bgm: list[str] = []
    if bgm_manifest.is_file():
        library = json.loads(bgm_manifest.read_text(encoding="utf-8"))
        missing_bgm = [item["file"] for item in library.get("tracks", []) if not (bgm_manifest.parent / item["file"]).is_file()]
    checks.append(result("BGM", "ok" if not missing_bgm else "optional_missing", "缺少: " + ", ".join(missing_bgm) if missing_bgm else "本地曲库完整"))

    videocut = Path(os.environ.get("VIDEOCUT_ROOT", str(ROOT.parent / "videocut"))).expanduser()
    checks.append(result("剪映草稿 videocut", "ok" if (videocut / "src").is_dir() else "optional_missing", str(videocut)))

    grok = shutil.which("grok")
    checks.append(result("Grok CLI", "ok" if grok else "optional_missing", grok or "只影响可选动态视频"))

    ltx_root_value = os.environ.get("LTX_VIDEO_LOCAL_ROOT", "").strip()
    if ltx_root_value:
        ltx_root = Path(ltx_root_value).expanduser().resolve()
        ltx_ready = (
            (ltx_root / "run_i2v_hq.sh").is_file()
            and model_index_complete(ltx_root / "models/LTX-2.3-dev/transformer/model.safetensors.index.json")
            and model_index_complete(ltx_root / "models/gemma-3-12b-it-4bit/model.safetensors.index.json")
        )
        ltx_detail = f"{ltx_root}；文件完整，仍需单镜头 probe" if ltx_ready else f"{ltx_root}；模型或分片不完整"
        checks.append(result("LTX-2.3 本地视频", "ok" if ltx_ready else "optional_missing", ltx_detail))
    else:
        checks.append(result("LTX-2.3 本地视频", "optional_missing", "未设置 LTX_VIDEO_LOCAL_ROOT；不影响 FFmpeg 回退"))

    for item in checks:
        icon = {"ok": "OK", "missing": "MISSING", "optional_missing": "OPTIONAL"}[item["state"]]
        print(f"[{icon:8}] {item['name']}: {item['detail']}")

    required_missing = [item for item in checks if item["state"] == "missing"]
    print(f"\n必需缺失 {len(required_missing)} 项；可选缺失 {sum(item['state'] == 'optional_missing' for item in checks)} 项。")
    return 1 if required_missing else 0


if __name__ == "__main__":
    raise SystemExit(main())

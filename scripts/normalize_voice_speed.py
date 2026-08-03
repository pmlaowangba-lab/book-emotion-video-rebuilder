#!/usr/bin/env python3
"""将已生成的连续配音归一到参考片锁定的 4.56 汉字/秒。

只允许小幅、保持音高的 atempo 归一。测量跨度必须来自 TTS
的字级时间戳：首个可听汉字起点到最后一个可听汉字终点。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


TARGET_CPS = 4.56
TOLERANCE_CPS = 0.02
MAX_CORRECTION = 0.08


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="将配音归一到固定 4.56 汉字/秒")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--han-count", required=True, type=int)
    parser.add_argument("--first-word-start", required=True, type=float)
    parser.add_argument("--last-word-end", required=True, type=float)
    parser.add_argument("--target-cps", type=float, default=TARGET_CPS)
    parser.add_argument("--tolerance-cps", type=float, default=TOLERANCE_CPS)
    parser.add_argument("--max-correction", type=float, default=MAX_CORRECTION)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    source = args.input.expanduser().resolve()
    output = args.output.expanduser().resolve()
    report_path = args.report.expanduser().resolve() if args.report else None

    if not source.is_file():
        parser.error(f"输入音频不存在：{source}")
    if output.exists():
        parser.error(f"输出已存在，请使用新版本号：{output}")
    if args.han_count <= 0:
        parser.error("--han-count 必须大于 0")
    if args.first_word_start < 0 or args.last_word_end <= args.first_word_start:
        parser.error("首字/末字时间戳无效")
    if args.target_cps <= 0 or args.tolerance_cps < 0:
        parser.error("语速目标或容差无效")

    raw_span = args.last_word_end - args.first_word_start
    raw_cps = args.han_count / raw_span
    tempo_factor = args.target_cps / raw_cps
    correction = abs(tempo_factor - 1.0)
    if correction > args.max_correction + 1e-9:
        raise SystemExit(
            f"需要的归一幅度为 {correction:.2%}，超过 {args.max_correction:.2%}；"
            "请返回检查标点、句式和 TTS 时间戳，禁止强压。"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    input_duration = probe_duration(source)
    already_locked = abs(raw_cps - args.target_cps) <= args.tolerance_cps
    if already_locked:
        shutil.copy2(source, output)
        applied_factor = 1.0
    else:
        applied_factor = tempo_factor
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(source),
                "-vn",
                "-af",
                f"atempo={applied_factor:.9f}",
                "-c:a",
                "pcm_s16le",
                str(output),
            ],
            check=True,
        )

    output_duration = probe_duration(output)
    normalized_start = args.first_word_start / applied_factor
    normalized_end = args.last_word_end / applied_factor
    normalized_span = normalized_end - normalized_start
    measured_cps = args.han_count / normalized_span
    report = {
        "speed_mode": "reference_locked",
        "reference_video_id": "7668678283642779072",
        "input": str(source),
        "output": str(output),
        "han_count": args.han_count,
        "target_chars_per_second": args.target_cps,
        "tolerance_chars_per_second": args.tolerance_cps,
        "raw_chars_per_second": round(raw_cps, 6),
        "tempo_factor": round(applied_factor, 9),
        "normalization_applied": not already_locked,
        "normalization_method": "ffmpeg_atempo_pitch_preserving",
        "input_duration_seconds": round(input_duration, 6),
        "output_duration_seconds": round(output_duration, 6),
        "first_word_start_seconds": round(normalized_start, 6),
        "last_word_end_seconds": round(normalized_end, 6),
        "speech_span_seconds": round(normalized_span, 6),
        "chars_per_second": round(measured_cps, 6),
        "passed": abs(measured_cps - args.target_cps) <= args.tolerance_cps,
    }
    if report_path:
        if report_path.exists():
            parser.error(f"报告已存在，请使用新版本号：{report_path}")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

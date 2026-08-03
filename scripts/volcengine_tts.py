#!/usr/bin/env python3
"""Volcengine TTS v3 via env-separated credentials.

Reads ``assets/volcengine.env`` and writes a 24 kHz mono WAV. Credentials are
used only in request headers and are never printed or persisted in outputs.
"""
import os, sys, json, requests, base64, uuid, wave
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = SKILL_ROOT / "assets" / "volcengine.env"

def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def volcengine_tts(text: str, output_path: str, speaker: str = None, speech_rate: int = 10):
    env = load_env()
    api_key = env.get("VOLCENGINE_API_KEY")
    if not api_key:
        raise RuntimeError("VOLCENGINE_API_KEY not found in volcengine.env")
    speaker = speaker or env.get("VOLCENGINE_SPEAKER", "S_Bkoh3uBT1")

    # S_* is a cloned voice and must use the ICL resource. Public voices use
    # Seed-TTS 2.0. An explicit env value can override this routing.
    resource_id = env.get("VOLCENGINE_RESOURCE_ID") or (
        "seed-icl-2.0" if speaker.startswith("S_") else "seed-tts-2.0"
    )
    url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
    headers = {
        "X-Api-Key": api_key,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": str(uuid.uuid4()),
        "Content-Type": "application/json",
    }
    payload = {
        "user": {"uid": "book-video-builder"},
        "req_params": {
            "text": text,
            "speaker": speaker,
            "audio_params": {
                "format": "pcm",
                "sample_rate": 24000,
                # The Skill's legacy provider value 10 means normal speed.
                # V3 expresses the same setting as 0 on its native scale.
                "speech_rate": int(round((speech_rate / 10.0 - 1.0) * 100)),
            },
            "additions": json.dumps({"enable_timestamp": False}),
        },
    }

    r = requests.post(url, headers=headers, json=payload, timeout=120, stream=True)
    if not r.ok:
        raise RuntimeError(
            f"Volcengine TTS HTTP {r.status_code}: {r.text[:500]} "
            f"(logid={r.headers.get('X-Tt-Logid', 'unknown')})"
        )
    audio_chunks = []
    for raw_line in r.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        result = json.loads(raw_line)
        code = result.get("code", 0)
        if code not in (0, 20000000):
            raise RuntimeError(
                f"Volcengine TTS error: code={code}, message={result.get('message')}"
            )
        audio_b64 = result.get("data")
        if audio_b64:
            audio_chunks.append(base64.b64decode(audio_b64))
    if not audio_chunks:
        raise RuntimeError("Volcengine TTS returned no audio data")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(output_path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(b"".join(audio_chunks))
    print(f"TTS saved: {output_path} ({os.path.getsize(output_path)} bytes)")
    return output_path

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python volcengine_tts.py <text_file|text> <output.wav> [speaker] [rate]")
        sys.exit(1)

    text_input = sys.argv[1]
    if os.path.exists(text_input):
        text = Path(text_input).read_text().strip()
    else:
        text = text_input

    output = sys.argv[2]
    speaker = sys.argv[3] if len(sys.argv) > 3 else None
    rate = int(sys.argv[4]) if len(sys.argv) > 4 else 10

    volcengine_tts(text, output, speaker, rate)

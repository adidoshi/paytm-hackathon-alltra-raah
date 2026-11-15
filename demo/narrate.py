"""Generate the English narration for each scene with Sarvam text-to-speech.

Run from the repo root:  api/.venv/Scripts/python -m demo.narrate
Writes demo/out/audio/<scene>.wav and demo/out/durations.json (seconds per scene).
"""
from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

from api.services import sarvam

DEMO = Path(__file__).parent
OUT = DEMO / "out" / "audio"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if not sarvam.enabled():
        sys.exit("SARVAM_API_KEY is not set in .env")
    OUT.mkdir(parents=True, exist_ok=True)
    scenes = json.loads((DEMO / "scenes.json").read_text(encoding="utf-8"))
    durations = {}
    for s in scenes:
        if not s["say"]:
            durations[s["id"]] = 0
            continue
        audio, cached = sarvam.tts(s["say"], "en")
        path = OUT / f"{s['id']}.wav"
        path.write_bytes(audio)
        with wave.open(str(path)) as w:
            durations[s["id"]] = round(w.getnframes() / w.getframerate(), 2)
        print(f"{s['id']:16} {durations[s['id']]:5.1f}s {'(cached)' if cached else ''}")
    (DEMO / "out" / "durations.json").write_text(json.dumps(durations, indent=1), encoding="utf-8")
    print(f"total narration {sum(durations.values()):.0f}s")


if __name__ == "__main__":
    main()

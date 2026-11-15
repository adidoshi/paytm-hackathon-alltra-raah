"""Pre-generate every rejection explanation and its Sarvam audio before the demo.

Run from the repo root:  api/.venv/Scripts/python -m api.scripts.pregen
Results land in api/data/llm_cache and api/data/audio. On stage they are served from disk:
no credits used, nothing to fail on bad Wi-Fi. Re-run after changing a prompt, persona or voice.
"""
from __future__ import annotations

import os
import sys
import tempfile

# Work on a scratch database so the running API's demo state is untouched.
os.environ["RAAH_DB"] = os.path.join(tempfile.mkdtemp(), "pregen.db")
os.environ["SARVAM_MCP"] = "0"

from .. import db  # noqa: E402
from ..services import journey, sarvam  # noqa: E402


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if not sarvam.enabled():
        sys.exit("SARVAM_API_KEY is not set in .env")
    db.init()
    for p in journey.personas():
        for lang in ("mr", "hi", "en"):
            s = journey.apply(p["user_id"], None, None, lang)
            e = s["explanation"][lang]
            _, cached = sarvam.tts(e["text"], lang)
            print(f"{p['user_id']:7} {lang}  text: {e['source']:8} {e['model']:28} audio: {'cached' if cached else 'generated'}")
    print("\nDone. Commit api/data/llm_cache and api/data/audio to ship these with the repo.")


if __name__ == "__main__":
    main()

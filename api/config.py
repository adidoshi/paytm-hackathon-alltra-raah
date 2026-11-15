from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

API_DIR = Path(__file__).parent
ROOT = API_DIR.parent
load_dotenv(ROOT / ".env")
load_dotenv(API_DIR / ".env")

DATA_DIR = API_DIR / "data"
PERSONA_DIR = DATA_DIR / "personas"
AUDIO_DIR = DATA_DIR / "audio"
DB_PATH = Path(os.getenv("RAAH_DB", str(DATA_DIR / "raah.db")))


def env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


GEMINI_API_KEY = env("GEMINI_API_KEY") or env("GOOGLE_API_KEY")
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-2.5-flash")
SARVAM_API_KEY = env("SARVAM_API_KEY")
SARVAM_TTS_MODEL = env("SARVAM_TTS_MODEL", "bulbul:v3")
SARVAM_TTS_SPEAKER = env("SARVAM_TTS_SPEAKER")
SARVAM_STT_MODEL = env("SARVAM_STT_MODEL", "saaras:v3")
SARVAM_MCP_URL = env("SARVAM_MCP_URL")
CORS_ORIGINS = [o.strip() for o in env("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

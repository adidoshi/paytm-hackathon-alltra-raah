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
LLM_CACHE_DIR = DATA_DIR / "llm_cache"
DB_PATH = Path(os.getenv("RAAH_DB", str(DATA_DIR / "raah.db")))


def env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


GEMINI_API_KEY = env("GEMINI_API_KEY") or env("GOOGLE_API_KEY")
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-2.5-flash")
SARVAM_API_KEY = env("SARVAM_API_KEY")
SARVAM_TTS_MODEL = env("SARVAM_TTS_MODEL", "bulbul:v4-flash")
SARVAM_STT_MODEL = env("SARVAM_STT_MODEL", "saaras:v4")
SARVAM_CHAT_MODEL = env("SARVAM_CHAT_MODEL", "sarvam-105b-conversations")
# One voice per language. SARVAM_TTS_SPEAKER overrides all three.
SARVAM_SPEAKERS = {
    "en": env("SARVAM_SPEAKER_EN") or env("SARVAM_TTS_SPEAKER").lower() or "shubh_enhi_banking",
    "hi": env("SARVAM_SPEAKER_HI") or env("SARVAM_TTS_SPEAKER").lower() or "shubh_enhi_banking",
    "mr": env("SARVAM_SPEAKER_MR") or env("SARVAM_TTS_SPEAKER").lower() or "nilesh_mr_conversation",
}
# Explanation wording: "sarvam" (Sarvam-105B, best for Hindi and Marathi) or "gemini"
EXPLAIN_LLM = env("EXPLAIN_LLM", "sarvam")
# Ask Raah tool-calling agent: "sarvam" (Sarvam-105B, about 1 s) or "gemini"; the other is the fallback
AGENT_LLM = env("AGENT_LLM", "sarvam")
# Attach Sarvam's MCP tools (translate, identify language) to the chat agent: "1" to enable
SARVAM_MCP = env("SARVAM_MCP", "1") == "1"
CORS_ORIGINS = [o.strip() for o in env("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

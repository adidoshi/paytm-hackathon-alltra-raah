"""Sarvam AI through the official SDK (sarvamai).

- tts:  Bulbul text-to-speech, one voice per language
- stt:  Saaras speech-to-text with automatic language detection
- chat: Sarvam-105B chat completion, used to phrase explanations in Indic languages

Audio and LLM text are cached on disk, so a repeated line costs no credits and the
demo says the same thing every time.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from functools import lru_cache

from .. import config
from ..rules.i18n import LANGS


class SarvamError(RuntimeError):
    pass


def enabled() -> bool:
    return bool(config.SARVAM_API_KEY)


@lru_cache(maxsize=1)
def _client():
    if not enabled():
        raise SarvamError("SARVAM_API_KEY is not set")
    from sarvamai import SarvamAI

    return SarvamAI(api_subscription_key=config.SARVAM_API_KEY, timeout=40)


def speaker_for(lang: str) -> str:
    return config.SARVAM_SPEAKERS.get(lang) or config.SARVAM_SPEAKERS["en"]


def _key(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]


# ------------------------------------------------------------------ text-to-speech

def tts(text: str, lang: str) -> tuple[bytes, bool]:
    """Returns (wav bytes, served_from_cache)."""
    text = text.strip()[:2400]
    speaker = speaker_for(lang)
    path = config.AUDIO_DIR / f"{lang}-{_key(config.SARVAM_TTS_MODEL, speaker, lang, text)}.wav"
    if path.exists():
        return path.read_bytes(), True
    try:
        r = _client().text_to_speech.convert(
            text=text,
            language_code=LANGS.get(lang, "en-IN"),
            model=config.SARVAM_TTS_MODEL,
            speaker=speaker,
        )
    except SarvamError:
        raise
    except Exception as e:
        raise SarvamError(f"TTS failed: {e}") from e
    if not r.audios:
        raise SarvamError("TTS returned no audio")
    audio = base64.b64decode("".join(r.audios))
    config.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)
    return audio, False


# ------------------------------------------------------------------ speech-to-text

def stt(audio: bytes, filename: str, content_type: str) -> dict:
    """Up to 30 seconds of audio. Returns {"transcript", "lang" ("en"|"hi"|"mr"|None)}."""
    try:
        r = _client().speech_to_text.transcribe(
            file=(filename, audio, (content_type or "audio/webm").split(";")[0]),
            model=config.SARVAM_STT_MODEL,
            mode="transcribe",
            language_code="unknown",  # let Saaras detect the language
        )
    except SarvamError:
        raise
    except Exception as e:
        raise SarvamError(f"STT failed: {e}") from e
    code = (r.language_code or "")[:2]
    return {"transcript": (r.transcript or "").strip(), "lang": code if code in LANGS else None}


# ------------------------------------------------------------------ chat (Sarvam-105B)

_THINK = re.compile(r"<think>.*?</think>", re.S)


def chat(system: str, user: str, max_tokens: int = 600, cache: bool = True) -> str | None:
    """One chat completion. Cached by prompt, so the same facts always give the same wording."""
    if not enabled():
        return None
    path = config.LLM_CACHE_DIR / f"sarvam-{_key(config.SARVAM_CHAT_MODEL, system, user)}.json"
    if cache and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["text"]
    try:
        r = _client().chat.completions(
            model=config.SARVAM_CHAT_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.2,
            max_tokens=max_tokens,
            reasoning_effort="low",
        )
        text = _THINK.sub("", r.choices[0].message.content or "").strip()
    except Exception:
        return None
    if text and cache:
        config.LLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"text": text}, ensure_ascii=False), encoding="utf-8")
    return text or None

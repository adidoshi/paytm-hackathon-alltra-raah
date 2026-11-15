"""Sarvam AI: text-to-speech (Bulbul) and speech-to-text (Saaras) over REST.

Audio is cached on disk by hash(text + language + model), so repeated lines cost no credits
and the hero persona's audio can be committed to the repo before the demo.
"""
from __future__ import annotations

import base64
import hashlib

import httpx

from .. import config
from ..rules.i18n import LANGS

BASE = "https://api.sarvam.ai"


class SarvamError(RuntimeError):
    pass


def enabled() -> bool:
    return bool(config.SARVAM_API_KEY)


def _headers() -> dict:
    return {"api-subscription-key": config.SARVAM_API_KEY}


def _cache_path(text: str, lang: str):
    key = hashlib.sha256(f"{config.SARVAM_TTS_MODEL}|{config.SARVAM_TTS_SPEAKER}|{lang}|{text}".encode("utf-8")).hexdigest()[:24]
    return config.AUDIO_DIR / f"{lang}-{key}.wav"


def tts(text: str, lang: str) -> tuple[bytes, bool]:
    """Returns (wav bytes, served_from_cache)."""
    text = text.strip()[:2400]
    path = _cache_path(text, lang)
    if path.exists():
        return path.read_bytes(), True
    if not enabled():
        raise SarvamError("SARVAM_API_KEY is not set")
    body = {"text": text, "target_language_code": LANGS.get(lang, "en-IN"), "model": config.SARVAM_TTS_MODEL}
    if config.SARVAM_TTS_SPEAKER:
        body["speaker"] = config.SARVAM_TTS_SPEAKER
    with httpx.Client(timeout=30) as client:
        r = client.post(f"{BASE}/text-to-speech", headers=_headers(), json=body)
        if r.status_code in (400, 422):
            # Field name differs between API versions.
            body["language_code"] = body.pop("target_language_code")
            r = client.post(f"{BASE}/text-to-speech", headers=_headers(), json=body)
    if r.status_code >= 400:
        raise SarvamError(f"TTS {r.status_code}: {r.text[:300]}")
    audios = r.json().get("audios") or []
    if not audios:
        raise SarvamError("TTS returned no audio")
    audio = base64.b64decode("".join(audios))
    config.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)
    return audio, False


def stt(audio: bytes, filename: str, content_type: str) -> dict:
    """Returns {"transcript": str, "lang": "en" | "hi" | "mr" | None}. Up to 30 seconds of audio."""
    if not enabled():
        raise SarvamError("SARVAM_API_KEY is not set")
    with httpx.Client(timeout=45) as client:
        r = client.post(
            f"{BASE}/speech-to-text",
            headers=_headers(),
            files={"file": (filename, audio, content_type.split(";")[0] or "audio/webm")},
            data={"model": config.SARVAM_STT_MODEL, "mode": "transcribe"},
        )
    if r.status_code >= 400:
        raise SarvamError(f"STT {r.status_code}: {r.text[:300]}")
    data = r.json()
    code = (data.get("language_code") or "")[:2]
    return {"transcript": (data.get("transcript") or "").strip(), "lang": code if code in LANGS else None}

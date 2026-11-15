"""LLM access plus the number guard. The LLM phrases facts; it never produces them.

- Sarvam-105B phrases the rejection explanation (strongest in Hindi and Marathi).
- Gemini orchestrates the Ask Raah tool-calling agent, and backs up the explanation.
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache

from .. import config
from ..services import sarvam

LANG_NAMES = {"en": "simple Indian English", "hi": "simple everyday Hindi (Devanagari)", "mr": "simple everyday Marathi (Devanagari)"}

_DEVANAGARI = str.maketrans("०१२३४५६७८९", "0123456789")
_ALWAYS_OK = {"30", "60", "90", "300", "900", "100"}


@lru_cache(maxsize=1)
def get_llm():
    if not config.GEMINI_API_KEY:
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        kw = dict(model=config.GEMINI_MODEL, google_api_key=config.GEMINI_API_KEY, temperature=0.3, timeout=12, max_retries=0)
        try:
            return ChatGoogleGenerativeAI(**kw, thinking_level="minimal")  # thinking off: answers in about 1 s
        except Exception:
            return ChatGoogleGenerativeAI(**kw)
    except Exception:
        return None


def _numbers(text: str) -> set[str]:
    text = text.translate(_DEVANAGARI)
    out = set()
    for raw in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        n = raw.replace(",", "")
        if "." in n:
            n = n.rstrip("0").rstrip(".")
        out.add(n)
    return out


def numbers_ok(text: str, facts) -> tuple[bool, list[str]]:
    """True when every number in the LLM text also appears in the facts it was given."""
    allowed = _numbers(json.dumps(facts, ensure_ascii=False)) | _ALWAYS_OK
    bad = [n for n in _numbers(text) if n not in allowed and not (n.isdigit() and int(n) <= 12)]
    return (not bad, bad)


def text_of(message) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, list):
        content = " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return str(content).strip()


STYLE = {
    "en": "Write in simple Indian English.",
    "hi": "Write in everyday Hindi in Devanagari, the way a helpful bank officer in Pune would speak. Common words like loan, EMI, credit card and FD may stay in English; write everything else in Hindi.",
    "mr": "Write in everyday Marathi in Devanagari, the way a helpful bank officer in Pune would speak. Common words like loan, EMI, credit card and FD may stay in English; write everything else in Marathi, not English.",
}

EXPLAIN_SYSTEM = """You are Raah, a warm and respectful guide inside the Paytm app for someone whose loan was just rejected.
{style}
Write 3 or 4 short sentences that sound natural when read aloud. No bullet points, no markdown, no greeting line.
1. Say plainly that the loan was not approved this time, and the main reason, with its key figure from the JSON.
2. Say there is something they can start today.
3. Say Raah has made a 90-day plan from their own Paytm payments to get them ready to apply again.
Rules:
- Use only facts in the JSON. Never state a number, amount, rate or date that is not in it. Write numbers in digits.
- Do not say whether a future application will be approved, and do not talk about what Raah cannot do.
- Output only the explanation."""


def _gemini(system: str, user: str) -> str | None:
    llm = get_llm()
    if llm is None:
        return None
    path = config.LLM_CACHE_DIR / f"gemini-{hashlib.sha256(f'{config.GEMINI_MODEL}|{system}|{user}'.encode()).hexdigest()[:24]}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["text"]
    try:
        text = text_of(llm.invoke([("system", system), ("human", user)]))
    except Exception:
        return None
    if text:
        config.LLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"text": text}, ensure_ascii=False), encoding="utf-8")
    return text or None


def providers() -> list[str]:
    order = ["sarvam", "gemini"] if config.EXPLAIN_LLM == "sarvam" else ["gemini", "sarvam"]
    return [p for p in order if (p == "sarvam" and sarvam.enabled()) or (p == "gemini" and get_llm() is not None)]


def model_name(provider: str) -> str:
    return config.SARVAM_CHAT_MODEL if provider == "sarvam" else config.GEMINI_MODEL


def compose(provider: str, facts: dict, lang: str) -> str | None:
    system = EXPLAIN_SYSTEM.format(style=STYLE.get(lang, STYLE["en"]))
    user = json.dumps(facts, ensure_ascii=False)
    return sarvam.chat(system, user) if provider == "sarvam" else _gemini(system, user)


def agent_providers() -> list[str]:
    order = ["sarvam", "gemini"] if config.AGENT_LLM == "sarvam" else ["gemini", "sarvam"]
    return [p for p in order if (p == "sarvam" and sarvam.enabled()) or (p == "gemini" and get_llm() is not None)]


def agent_model(provider: str):
    if provider == "gemini":
        return get_llm()
    from .sarvam_chat import ChatSarvam

    return ChatSarvam()

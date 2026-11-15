"""Gemini access plus the number guard. The LLM phrases facts; it never produces them."""
from __future__ import annotations

import json
import re
from functools import lru_cache

from .. import config

LANG_NAMES = {"en": "simple Indian English", "hi": "simple everyday Hindi (Devanagari)", "mr": "simple everyday Marathi (Devanagari)"}

_DEVANAGARI = str.maketrans("०१२३४५६७८९", "0123456789")
_ALWAYS_OK = {"30", "60", "90", "300", "900", "100"}


@lru_cache(maxsize=1)
def get_llm():
    if not config.GEMINI_API_KEY:
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            google_api_key=config.GEMINI_API_KEY,
            temperature=0.3,
            timeout=12,
            max_retries=1,
        )
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


EXPLAIN_SYSTEM = """You are Raah, a respectful guide inside the Paytm app for someone whose loan was just rejected.
Write a short spoken explanation in {language}: 3 or 4 short sentences, warm and direct, no jargon, no bullet points, no markdown.
Rules you must follow:
- Use only the facts in the JSON. Never state a number, amount, rate or date that is not in the JSON.
- Copy rupee amounts and percentages exactly as written.
- Say why the loan was rejected, then that there is a step available today and a 90-day plan.
- Never promise approval and never give a credit decision yourself."""


def compose_explanation(facts: dict, lang: str) -> str | None:
    llm = get_llm()
    if llm is None:
        return None
    try:
        msg = llm.invoke(
            [
                ("system", EXPLAIN_SYSTEM.format(language=LANG_NAMES.get(lang, LANG_NAMES["en"]))),
                ("human", json.dumps(facts, ensure_ascii=False)),
            ]
        )
        return text_of(msg) or None
    except Exception:
        return None

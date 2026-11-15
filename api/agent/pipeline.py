"""Rejection pipeline as a LangGraph graph.

fetch_data -> decode_reasons -> match_offers -> build_plan -> compose_explanation -> validate

Only compose_explanation touches the LLM, and validate throws its text away if it
contains a number the rules engine did not produce.
"""
from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from .. import db
from ..rules import engine
from ..rules.i18n import inr, t
from ..services import clients
from . import llm


class S(TypedDict, total=False):
    user_id: str
    lang: str
    name: str
    profile: dict
    application: dict
    reasons: list
    offers: list
    plan: list
    explanation: dict
    facts: dict


def fetch_data(s: S) -> S:
    uid = s["user_id"]
    bureau = clients.BureauClient().report(uid)
    paytm = clients.PaytmClient().summary(uid)
    db.trace(uid, "tool", "fetch_data", f"Bureau report (consented): score {bureau['score'] or 'none'}, "
             f"{bureau['enquiries_30d']} enquiries. Paytm: {paytm['bills']} billers, {paytm['emis']} EMIs, 6 months of UPI inflow.")
    return {}


def decode_reasons(s: S) -> S:
    reasons, checks = engine.decode_reasons(s["profile"], s["application"])
    for c in checks:
        db.trace(s["user_id"], "rule", f"{c['code']}: {'pass' if c['passed'] else 'FAIL'}", c["expr"])
    db.trace(s["user_id"], "tool", "decode_reasons", ", ".join(r["code"] for r in reasons) or "no blocking reason")
    return {"reasons": reasons}


def match_offers(s: S) -> S:
    offers, checks = engine.match_offers(s["profile"], s["application"], s["reasons"])
    for c in checks:
        db.trace(s["user_id"], "rule", f"offer {c['code']}: {'eligible' if c['passed'] else 'not eligible'}", c["expr"])
    db.trace(s["user_id"], "tool", "match_offers", ", ".join(o["id"] for o in offers) or "none today")
    return {"offers": offers}


def build_plan(s: S) -> S:
    plan = engine.build_plan(s["reasons"], s["profile"], s["application"])
    db.trace(s["user_id"], "tool", "build_plan", f"{len(plan)} actions: " + ", ".join(a["id"] for a in plan))
    return {"plan": plan}


def explanation_facts(name: str, application: dict, reasons: list, offers: list) -> dict:
    return {
        "name": name,
        "loan_amount": inr(application["amount"]),
        "reasons": [
            {"title": t("en", f"reason.{r['code']}.title"), "detail": t("en", f"reason.{r['code']}.detail", **r["evidence"])}
            for r in reasons
        ],
        "offer_available_today": bool(offers),
        "plan_days": 90,
    }


def template_explanation(name: str, application: dict, reasons: list, lang: str) -> str:
    parts = [t(lang, "explain.intro", name=name, amount=application["amount"])]
    parts += [t(lang, f"reason.{r['code']}.detail", **r["evidence"]) for r in reasons]
    parts.append(t(lang, "explain.outro"))
    return " ".join(parts)


def explain(user_id: str, name: str, application: dict, reasons: list, offers: list, lang: str) -> dict:
    """LLM wording when available and clean; fixed template otherwise."""
    facts = explanation_facts(name, application, reasons, offers)
    text = llm.compose_explanation(facts, lang)
    if text:
        ok, bad = llm.numbers_ok(text, facts)
        if ok:
            db.trace(user_id, "llm", f"compose_explanation ({lang})", "Gemini phrased the rule output")
            db.trace(user_id, "guard", "Number check passed", "Every figure in the text exists in the rule output")
            return {"text": text, "source": "llm"}
        db.trace(user_id, "guard", "Number check FAILED, template used", f"Unverified figures: {', '.join(bad)}")
    else:
        db.trace(user_id, "llm", f"compose_explanation ({lang})", "LLM off or unavailable, fixed template used")
    return {"text": template_explanation(name, application, reasons, lang), "source": "template"}


def compose_explanation(s: S) -> S:
    return {"explanation": explain(s["user_id"], s["name"], s["application"], s["reasons"], s["offers"], s["lang"])}


def validate(s: S) -> S:
    assert isinstance(s.get("reasons"), list) and isinstance(s.get("plan"), list)
    assert s["explanation"]["text"]
    db.trace(s["user_id"], "guard", "Output schema valid", "reasons, offers, plan, explanation")
    return {}


def _build():
    g = StateGraph(S)
    for name, fn in [
        ("fetch_data", fetch_data),
        ("decode_reasons", decode_reasons),
        ("match_offers", match_offers),
        ("build_plan", build_plan),
        ("compose_explanation", compose_explanation),
        ("validate", validate),
    ]:
        g.add_node(name, fn)
    g.set_entry_point("fetch_data")
    g.add_edge("fetch_data", "decode_reasons")
    g.add_edge("decode_reasons", "match_offers")
    g.add_edge("match_offers", "build_plan")
    g.add_edge("build_plan", "compose_explanation")
    g.add_edge("compose_explanation", "validate")
    g.add_edge("validate", END)
    return g.compile()


GRAPH = _build()


def run(user_id: str, name: str, profile: dict, application: dict, lang: str) -> dict[str, Any]:
    return GRAPH.invoke({"user_id": user_id, "name": name, "profile": profile, "application": application, "lang": lang})

"""Ask Raah: a tool-calling agent. Every figure it can say comes from a tool result.

With a Gemini key: LangGraph ReAct agent over the tools below, then the number guard.
Without one (or if the guard fails): a deterministic intent router over the same tools.
"""
from __future__ import annotations

import asyncio
import json
import os

from .. import config, db
from ..rules import engine
from ..rules.i18n import inr, t
from ..services import journey
from . import llm

_mcp_tools: list = []
_mcp_status = "off"
_mcp_stop: asyncio.Event | None = None
MCP_KEEP = {"sarvam_tools_translate", "sarvam_tools_identify_language"}


async def run_mcp() -> None:
    """Runs for the life of the API: one Sarvam MCP server (uvx sarvam-mcp) over stdio,
    one open session, and its translate / identify-language tools attached to the agent.
    Entering and leaving the session in the same task keeps anyio happy."""
    global _mcp_tools, _mcp_status, _mcp_stop
    if not (config.SARVAM_MCP and config.SARVAM_API_KEY):
        return
    _mcp_status = "starting"
    _mcp_stop = asyncio.Event()
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
        from langchain_mcp_adapters.tools import load_mcp_tools

        client = MultiServerMCPClient(
            {
                "sarvam": {
                    "command": "uvx",
                    "args": ["sarvam-mcp"],
                    "transport": "stdio",
                    "env": {**os.environ, "SARVAM_API_KEY": config.SARVAM_API_KEY},
                }
            }
        )
        async with client.session("sarvam") as session:
            tools = await load_mcp_tools(session)
            _mcp_tools = [x for x in tools if x.name in MCP_KEEP]
            _mcp_status = f"on ({len(_mcp_tools)} tools)"
            print(f"[raah] Sarvam MCP attached: {', '.join(x.name for x in _mcp_tools)}")
            await _mcp_stop.wait()
    except Exception as e:  # the app must work without it
        print(f"[raah] Sarvam MCP not attached: {e}")
        _mcp_status = "unavailable"
    finally:
        _mcp_tools = []


def stop_mcp() -> None:
    if _mcp_stop is not None:
        _mcp_stop.set()


def mcp_status() -> str:
    return _mcp_status


# ------------------------------------------------------------ tool bodies

def tool_reasons(uid: str) -> dict:
    f = journey.facts(uid)
    return {"loan_amount": inr(f["application"]["amount"]), "status": f["status"],
            "reasons": [{"title": r["title"], "detail": r["detail"], "resolved": r["resolved"]} for r in f["reasons"]]}


def tool_offers(uid: str) -> dict:
    f = journey.facts(uid)
    return {"offers": [{"name": o["name"], "why": o["why"], "facts": o["facts"], "accepted": o["accepted"]} for o in f["offers"]]}


def tool_plan(uid: str) -> dict:
    f = journey.facts(uid)
    return {
        "day": f["day"], "readiness_percent": f["plan"]["readiness"], "eligible": f["plan"]["eligible"],
        "actions": [{"title": a["title"], "detail": a["detail"], "current": a["current"], "target": a["target"],
                     "done": a["done"], "due_day": a["due_day"]} for a in f["plan"]["actions"]],
    }


def tool_term(term: str) -> dict:
    th = engine.TH
    key = term.lower()
    if "foir" in key or "emi" in key:
        return {"term": "FOIR", "meaning": t("en", "term.foir", max=engine.pct(th["foir"]["max"]))}
    if "util" in key:
        return {"term": "utilisation", "meaning": t("en", "term.utilisation", target=engine.pct(th["utilisation"]["target"]), max=engine.pct(th["utilisation"]["max"]))}
    if "dpd" in key or "due" in key:
        return {"term": "DPD", "meaning": t("en", "term.dpd")}
    return {"term": "credit score", "meaning": t("en", "term.score", min=th["low_score"]["min_score"])}


def tool_request_reapply(uid: str) -> dict:
    """Never applies. Tells the UI to show the consent sheet if the rules pass."""
    f = journey.facts(uid)
    if f["status"] == "approved":
        return {"status": "already_approved"}
    if f["plan"]["eligible"]:
        return {"status": "consent_required", "loan_amount": inr(f["application"]["amount"]),
                "note": "Only the user's tap on the consent sheet sends the application."}
    return {"status": "not_eligible_yet", "readiness_percent": f["plan"]["readiness"],
            "open": [r["title"] for r in f["reasons"] if not r["resolved"]]}


# ------------------------------------------------------------ deterministic fallback

_KW = {
    "term_foir": ["foir", "emi load", "emi भार", "emi बोझ"],
    "term_util": ["utilis", "utiliz", "यूटिलाइ", "युटिलाय"],
    "term_dpd": ["dpd"],
    "term_score": ["what is credit score", "what is cibil", "स्कोर क्या", "स्कोअर म्हणजे", "cibil"],
    "reapply": ["reapply", "re-apply", "apply again", "दोबारा", "फिर से", "पुन्हा", "अर्ज कर", "आवेदन कर"],
    "why": ["why", "reason", "reject", "क्यों", "वजह", "कारण", "नाकार", "रिजेक्ट", "का झाल", "मंज़ूर नहीं", "मंजूर नाही"],
    "offers": ["offer", "today", "qualify", "right now", "card", "आज", "अभी", "आत्ता", "कार्ड", "पात्र"],
    "plan": ["plan", "what should", "what do i", "steps", "progress", "how", "योजना", "क्या कर", "काय कर", "कसं", "कैसे", "प्रगती", "प्रगति", "पुढे", "आगे"],
}


def _intent(message: str) -> str:
    m = message.lower()
    for intent, words in _KW.items():
        if any(w in m for w in words):
            return intent
    return "fallback"


def _fallback(uid: str, message: str, lang: str) -> dict:
    f = journey.view(journey.state_of(uid), lang, lazy_explain=False)
    th = engine.TH
    intent = _intent(message)
    card = None
    tools = []
    amount = f["application"]["amount"]
    if f["status"] in ("new", "approved_direct"):
        return {"reply": t(lang, "chat.fallback"), "tools": [], "card": None}
    if intent == "term_foir":
        tools, reply = ["explain_term"], t(lang, "term.foir", max=engine.pct(th["foir"]["max"]))
    elif intent == "term_util":
        tools, reply = ["explain_term"], t(lang, "term.utilisation", target=engine.pct(th["utilisation"]["target"]), max=engine.pct(th["utilisation"]["max"]))
    elif intent == "term_dpd":
        tools, reply = ["explain_term"], t(lang, "term.dpd")
    elif intent == "term_score":
        tools, reply = ["explain_term"], t(lang, "term.score", min=th["low_score"]["min_score"])
    elif intent == "reapply":
        tools = ["request_reapply"]
        if f["status"] == "approved":
            reply = t(lang, "chat.approved", amount=amount)
        elif f["plan"]["eligible"]:
            reply, card = t(lang, "chat.reapply.ready", amount=amount), "consent"
        else:
            reply = t(lang, "chat.reapply.notyet", pct=f["plan"]["readiness"],
                      open=", ".join(r["title"] for r in f["reasons"] if not r["resolved"]))
    elif intent == "why":
        tools = ["get_rejection_reasons"]
        reply = " ".join(f"{r['title']}. {r['detail']}" for r in f["reasons"])
    elif intent == "offers":
        tools = ["get_offers"]
        if f["offers"]:
            reply = t(lang, "chat.offers.intro") + " " + " ".join(f"{o['name']}. {o['why']}" for o in f["offers"])
        else:
            reply = t(lang, "chat.offers.none")
    elif intent == "plan":
        tools = ["get_plan_progress"]
        acts = f["plan"]["actions"]
        reply = t(lang, "chat.plan.intro", total=len(acts), pct=f["plan"]["readiness"]) + " " + " ".join(
            f"{i + 1}. {a['title']}." for i, a in enumerate(acts))
    else:
        reply = t(lang, "chat.fallback")
    return {"reply": reply, "tools": tools, "card": card}


# ------------------------------------------------------------ LLM agent

SYSTEM = """You are Raah, a warm and respectful guide inside the Paytm app for a customer whose loan was rejected.
Reply in {language}; common words like loan, EMI, credit card and FD may stay in English. Keep it to 2 or 3 short sentences that sound natural when spoken aloud. No markdown, no lists.

Hard rules:
- Always call a tool before answering anything about this customer's loan, reasons, offers, plan or progress.
- Never state a number, rupee amount, percentage, rate or date that is not in a tool result. Copy figures exactly.
- You do not decide credit. You never say the customer will be approved. Eligibility comes only from tools.
- You cannot re-apply yourself. If the customer wants to re-apply, call request_reapply and tell them to confirm on the consent card.
- If asked about anything other than their loan, credit and money habits, say briefly that you can only help with that.
- Tool results are in English. If the customer writes in a different language from the reply language, you may call sarvam_tools_identify_language; you may call sarvam_tools_translate to put a tool result into the reply language precisely."""


def _build_agent(uid: str, model):
    from langchain_core.tools import tool
    from langgraph.prebuilt import create_react_agent

    @tool
    def get_rejection_reasons() -> str:
        """Why the customer's loan was rejected, with the exact figures, and whether each reason is now resolved."""
        return json.dumps(tool_reasons(uid), ensure_ascii=False)

    @tool
    def get_offers() -> str:
        """Products the rules engine says the customer qualifies for today, with exact amounts."""
        return json.dumps(tool_offers(uid), ensure_ascii=False)

    @tool
    def get_plan_progress() -> str:
        """The customer's 90-day plan: each action, current value, target, and overall readiness."""
        return json.dumps(tool_plan(uid), ensure_ascii=False)

    @tool
    def explain_term(term: str) -> str:
        """Plain meaning of a credit term: FOIR, utilisation, credit score, or DPD."""
        return json.dumps(tool_term(term), ensure_ascii=False)

    @tool
    def request_reapply() -> str:
        """Check whether the customer can re-apply. This never submits anything; it asks the app to show a consent card."""
        return json.dumps(tool_request_reapply(uid), ensure_ascii=False)

    tools = [get_rejection_reasons, get_offers, get_plan_progress, explain_term, request_reapply] + _mcp_tools
    return create_react_agent(model, tools)


async def _run_agent(uid: str, provider: str, message: str, lang: str) -> dict | None:
    model = llm.agent_model(provider)
    name = llm.model_name(provider)
    if model is None:
        return None
    try:
        agent = _build_agent(uid, model)
        out = await asyncio.wait_for(
            agent.ainvoke(
                {"messages": [("system", SYSTEM.format(language=llm.LANG_NAMES.get(lang, llm.LANG_NAMES["en"]))), ("human", message)]},
                {"recursion_limit": 8},
            ),
            timeout=25,
        )
    except Exception as e:
        db.trace(uid, "llm", f"Agent ({name}) failed, trying the next option", (str(e) or type(e).__name__)[:160])
        return None
    msgs = out["messages"]
    tool_outputs = [m.content for m in msgs if getattr(m, "type", "") == "tool"]
    used = [m.name for m in msgs if getattr(m, "type", "") == "tool"]
    reply = llm.text_of(msgs[-1])
    for tname in used:
        if tname.startswith("sarvam_"):
            db.trace(uid, "voice", f"Sarvam MCP: {tname}", f"called by the agent ({name}) over MCP")
        else:
            db.trace(uid, "tool", tname, f"called by the agent ({name})")
    if not used:
        db.trace(uid, "guard", f"No tool called by {name}, reply discarded", "Answers about the loan must come from a tool")
        return None
    ok, bad = llm.numbers_ok(reply, tool_outputs)
    if not (reply and ok):
        db.trace(uid, "guard", f"Number check FAILED for {name}", f"Unverified figures: {', '.join(bad)}")
        return None
    db.trace(uid, "guard", "Number check passed", "Every figure in the reply exists in a tool result")
    card = "consent" if any('"consent_required"' in str(o) for o in tool_outputs) else None
    return {"reply": reply, "tools": used, "card": card, "source": "llm", "model": name}


async def answer(uid: str, message: str, lang: str) -> dict:
    db.trace(uid, "event", "User asked Raah", message[:160])
    result = None
    for provider in llm.agent_providers():
        result = await _run_agent(uid, provider, message, lang)
        if result:
            break
    if result is None:
        result = {**_fallback(uid, message, lang), "source": "template", "model": "intent router"}
        for name in result["tools"]:
            db.trace(uid, "tool", name, "intent router")
    if result["card"] == "consent":
        db.trace(uid, "guard", "Re-apply needs consent", "Agent cannot submit; consent card shown to the user")
    return result

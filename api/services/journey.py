"""The journey: apply -> rejected -> explain / offer / plan -> time passes -> eligible -> consent -> re-apply."""
from __future__ import annotations

import copy
import json

from .. import db
from ..agent import pipeline
from ..config import PERSONA_DIR
from ..rules import engine
from ..rules.i18n import T, inr, t
from . import clients

UNITS = {"utilisation": "%", "foir": "%"}
BINARY = {"fd_card_active", "bill_autopay", "emi_autopay"}


def personas() -> list[dict]:
    out = []
    for f in sorted(PERSONA_DIR.glob("*.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        out.append(
            {
                "user_id": p["user_id"], "name": p["name"], "first_name": p["first_name"], "age": p["age"],
                "city": p["city"], "occupation": p["occupation"], "language": p["language"],
                "monthly_income": p["profile"]["monthly_income"], "application": p["application"],
            }
        )
    order = {"ravi": 0, "priya": 1, "sameer": 2}
    return sorted(out, key=lambda p: order.get(p["user_id"], 9))


def _fresh(user_id: str) -> dict:
    path = PERSONA_DIR / f"{user_id}.json"
    if not path.exists():
        raise KeyError(user_id)
    p = json.loads(path.read_text(encoding="utf-8"))
    return {
        "user_id": user_id,
        "persona": {k: p[k] for k in ("name", "first_name", "age", "city", "occupation", "language")},
        "profile": p["profile"],
        "application": p["application"],
        "simulation": p["simulation"],
        "feed": [{**e, "day": e["day"]} for e in p["history"]],
        "status": "new",
        "day": 0,
        "reasons": [],
        "offers": [],
        "plan": [],
        "accepted_offers": [],
        "notifications": [],
        "explanation": {},
        "lender_ref": None,
    }


def reset(user_id: str | None = None) -> None:
    db.clear(user_id)
    ids = [user_id] if user_id else [p["user_id"] for p in personas()]
    for uid in ids:
        db.save_state(_fresh(uid))


def state_of(user_id: str) -> dict:
    s = db.get_state(user_id)
    if s is None:
        s = _fresh(user_id)
        db.save_state(s)
    return s


# ---------------------------------------------------------------- steps

def apply(user_id: str, amount: int | None, tenure_months: int | None, lang: str) -> dict:
    db.clear(user_id)
    s = _fresh(user_id)
    if amount:
        s["application"]["amount"] = int(amount)
    if tenure_months:
        s["application"]["tenure_months"] = int(tenure_months)
    db.save_state(s)
    app = s["application"]

    db.trace(user_id, "event", "loan.application.submitted", f"{app['product']}, {inr(app['amount'])}, {app['tenure_months']} months")
    decision = clients.LenderClient().apply(user_id, s["profile"], app)
    s["lender_ref"] = decision["reference"]
    db.trace(user_id, "lender", f"Lender decision: {decision['decision']}",
             f"ref {decision['reference']}" + (f", codes: {', '.join(decision['reason_codes'])}" if decision["reason_codes"] else ""))

    if decision["decision"] == "APPROVED":
        s["status"] = "approved_direct"
        db.save_state(s)
        return s

    db.trace(user_id, "event", "loan.rejected -> Raah agent triggered", "LangGraph rejection pipeline started")
    out = pipeline.run(user_id, s["persona"]["first_name"], s["profile"], app, lang)
    s.update(status="rejected", reasons=out["reasons"], offers=out["offers"], plan=out["plan"])
    s["explanation"][lang] = out["explanation"]
    db.save_state(s)
    return s


def _set_path(obj, path: str, value) -> None:
    keys = path.split(".")
    for k in keys[:-1]:
        obj = obj[int(k)] if isinstance(obj, list) else obj[k]
    last = keys[-1]
    if isinstance(obj, list):
        obj[int(last)] = value
    else:
        obj[last] = value


def advance(user_id: str) -> dict:
    """The demo clock: 30 days pass and that month's Paytm and bureau events land.
    The eligibility watcher then re-runs the rules."""
    s = state_of(user_id)
    if s["status"] not in ("rejected", "eligible"):
        return s
    idx = s["day"] // 30
    if idx >= len(s["simulation"]):
        return s
    before = engine.check_progress(s["plan"], s["profile"], s["application"])
    month = s["simulation"][idx]
    for path, value in month["set"].items():
        _set_path(s["profile"], path, value)
    s["day"] += 30
    for e in month["events"]:
        s["feed"].append({**e, "day": s["day"]})
        db.trace(user_id, "event", f"Paytm event: {e['source']}", e["text"] + (f" ({inr(e['amount'])})" if e["amount"] else ""))
    _watch(s, before)
    db.save_state(s)
    return s


def _watch(s: dict, before: dict) -> None:
    """Eligibility watcher. Runs whenever new data lands."""
    uid = s["user_id"]
    now = engine.check_progress(s["plan"], s["profile"], s["application"])
    db.trace(uid, "tool", "eligibility_watcher", f"day {s['day']}: readiness {now['readiness']}%, open: {', '.join(now['open_reasons']) or 'none'}")
    for c in now["checks"]:
        if not c["passed"] or c["code"] in {r["code"] for r in s["reasons"]}:
            db.trace(uid, "rule", f"{c['code']}: {'pass' if c['passed'] else 'FAIL'}", c["expr"])
    was_done = {a["id"] for a in before["actions"] if a["done"]}
    nid = len(s["notifications"])
    for a in now["actions"]:
        if a["done"] and a["id"] not in was_done:
            nid += 1
            s["notifications"].append({"id": nid, "day": s["day"], "kind": "done", "action_id": a["id"]})
    if now["eligible"]:
        s["status"] = "eligible"
        nid += 1
        s["notifications"].append({"id": nid, "day": s["day"], "kind": "eligible"})
        db.trace(uid, "nudge", "Nudge sent: now eligible", "All blocking rules pass. Waiting for the user's consent to re-apply.")
    else:
        nxt = next((a["id"] for a in now["actions"] if not a["done"]), None)
        nid += 1
        s["notifications"].append(
            {"id": nid, "day": s["day"], "kind": "month", "pct": now["readiness"],
             "done": sum(a["done"] for a in now["actions"]), "total": len(now["actions"]), "action_id": nxt}
        )
        db.trace(uid, "nudge", f"Nudge sent: {now['readiness']}% ready", f"next action: {nxt}")


def accept_offer(user_id: str, offer_id: str) -> dict:
    s = state_of(user_id)
    offer = next((o for o in s["offers"] if o["id"] == offer_id), None)
    if offer is None:
        raise ValueError("offer not available")
    if offer_id not in s["accepted_offers"]:
        db.consent(user_id, f"start {offer_id}", json.dumps(offer))
        s["accepted_offers"].append(offer_id)
        before = engine.check_progress(s["plan"], s["profile"], s["application"])
        if offer_id == "fd_card":
            s["profile"]["fd_card_active"] = True
            s["profile"]["cards"].append({"id": "fdcard", "name": "FD-backed card", "limit": offer["limit"], "balance": 0, "secured": True})
            s["feed"].append({"day": s["day"], "source": "FD", "text": "Fixed deposit opened, card issued", "amount": offer["fd_amount"], "dir": "out"})
        db.trace(user_id, "event", f"Offer accepted: {offer_id}", "Started with the user's consent")
        now = engine.check_progress(s["plan"], s["profile"], s["application"])
        was_done = {a["id"] for a in before["actions"] if a["done"]}
        for a in now["actions"]:
            if a["done"] and a["id"] not in was_done:
                s["notifications"].append({"id": len(s["notifications"]) + 1, "day": s["day"], "kind": "done", "action_id": a["id"]})
        db.save_state(s)
    return s


def reapply(user_id: str, consent: bool) -> dict:
    """Only ever called from the user's tap on the consent sheet."""
    s = state_of(user_id)
    if not consent:
        raise PermissionError("consent required")
    if s["status"] != "eligible":
        raise ValueError("not eligible yet")
    app = s["application"]
    db.consent(user_id, "re-apply", f"Share updated bureau and Paytm data with the lender and re-apply for {inr(app['amount'])}")
    decision = clients.LenderClient().apply(user_id, s["profile"], app)
    db.trace(user_id, "lender", f"Lender decision: {decision['decision']}", f"ref {decision['reference']}-R")
    if decision["decision"] == "APPROVED":
        s["status"] = "approved"
        db.trace(user_id, "event", "loan.approved", f"{inr(app['amount'])} approved {s['day']} days after the rejection")
    db.save_state(s)
    return s


# ---------------------------------------------------------------- view

def _fmt_value(metric: str, v: float) -> str:
    if metric in BINARY:
        return "on" if v else "off"
    return f"{int(v)}{UNITS.get(metric, '')}"


def _action_view(a: dict, lang: str) -> dict:
    return {
        "id": a["id"],
        "reason_code": a["reason_code"],
        "title": t(lang, f"action.{a['id']}.title", **a["params"]),
        "detail": t(lang, f"action.{a['id']}.detail", **a["params"]),
        "metric": a["metric"],
        "binary": a["metric"] in BINARY,
        "start": _fmt_value(a["metric"], a["start"]),
        "current": _fmt_value(a["metric"], a["current"]),
        "target": _fmt_value(a["metric"], a["target"]),
        "progress": a["progress"],
        "done": a["done"],
        "due_day": a["due_day"],
        "paytm_action": a["paytm_action"],
    }


def _offer_view(o: dict, lang: str, accepted: list[str]) -> dict:
    if o["id"] == "fd_card":
        params = {"fd": o["fd_amount"], "limit": o["limit"]}
        facts = [["FD", inr(o["fd_amount"])], ["Card limit", inr(o["limit"])], ["FD interest", f"{o['fd_rate'] * 100:.1f}% p.a."]]
    else:
        params = {"amount": o["amount"], "emi": o["emi"], "foir": o["foir"], "max": o["max_foir"]}
        facts = [["Amount", inr(o["amount"])], ["EMI", inr(o["emi"])], ["Tenure", f"{o['tenure_months']} months"], ["Rate", f"{o['rate'] * 100:.0f}% p.a."]]
    return {
        "id": o["id"],
        "name": t(lang, f"offer.{o['id']}.name", **params),
        "tagline": t(lang, f"offer.{o['id']}.tagline", **params),
        "why": t(lang, f"offer.{o['id']}.why", **params),
        "facts": facts,
        "accepted": o["id"] in accepted,
    }


def _notification_view(n: dict, s: dict, actions: dict[str, dict], lang: str) -> dict:
    amount = s["application"]["amount"]
    if n["kind"] == "eligible":
        title, body = t(lang, "nudge.eligible.title", amount=amount), t(lang, "nudge.eligible.body")
    elif n["kind"] == "done":
        title, body = t(lang, "nudge.done.title"), actions.get(n["action_id"], {}).get("title", "")
    else:
        nxt = actions.get(n.get("action_id") or "", {}).get("title", "")
        title = t(lang, "nudge.month.title", day=n["day"], pct=n["pct"])
        body = t(lang, "nudge.month.body", done=n["done"], total=n["total"], next=nxt)
    return {"id": n["id"], "day": n["day"], "kind": n["kind"], "title": title, "body": body}


def view(s: dict, lang: str, lazy_explain: bool = True) -> dict:
    if lang not in T:
        lang = "en"
    app = s["application"]
    m = engine.metrics(s["profile"], app)
    prog = engine.check_progress(s["plan"], s["profile"], app) if s["plan"] else None
    open_codes = set(prog["open_reasons"]) if prog else set()
    actions = [_action_view(a, lang) for a in prog["actions"]] if prog else []
    by_id = {a["id"]: a for a in actions}

    explanation = None
    if s["status"] in ("rejected", "eligible", "approved"):
        if lang not in s["explanation"] and lazy_explain:
            s["explanation"][lang] = pipeline.explain(s["user_id"], s["persona"]["first_name"], app, s["reasons"], s["offers"], lang)
            db.save_state(s)
        explanation = s["explanation"].get(lang)

    return {
        "user": {**s["persona"], "user_id": s["user_id"], "monthly_income": s["profile"]["monthly_income"]},
        "lang": lang,
        "status": s["status"],
        "day": s["day"],
        "can_advance": s["status"] in ("rejected", "eligible") and s["day"] // 30 < len(s["simulation"]),
        "application": {**app, "emi": m["proposed_emi"], "reference": s["lender_ref"]},
        "reasons": [
            {
                "code": r["code"],
                "title": t(lang, f"reason.{r['code']}.title"),
                "detail": t(lang, f"reason.{r['code']}.detail", **r["evidence"]),
                "resolved": r["code"] not in open_codes,
            }
            for r in s["reasons"]
        ],
        "explanation": explanation,
        "offers": [_offer_view(o, lang, s["accepted_offers"]) for o in s["offers"]],
        "plan": {
            "readiness": prog["readiness"] if prog else 0,
            "eligible": prog["eligible"] if prog else False,
            "actions": actions,
        },
        "notifications": [_notification_view(n, s, by_id, lang) for n in reversed(s["notifications"])],
        "feed": sorted(s["feed"], key=lambda e: -e["day"]),
        "snapshot": {
            "score": s["profile"].get("score"),
            "utilisation": engine.pct(m["utilisation"]) if m["card_limit"] else None,
            "foir": engine.pct(m["foir"]),
            "on_time_cycles": s["profile"]["on_time_cycles"],
        },
    }


def facts(user_id: str) -> dict:
    """English, number-exact facts for the chat agent's tools."""
    return view(copy.deepcopy(state_of(user_id)), "en", lazy_explain=False)

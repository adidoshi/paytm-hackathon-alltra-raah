"""Reading the customer's bank statements (Account Aggregator) and Paytm records.

read()     consent -> fetch -> LLM reader labels every row -> rules build the cash-flow profile
           -> reasons, offers and plan are re-run on the new evidence
refresh()  each new month of data: the reader labels only the new rows, the profile is rebuilt
view()     what the phone and the stage show
"""
from __future__ import annotations

import math

from .. import db
from ..agent import reader
from ..rules import cashflow, engine
from ..rules.i18n import inr, t
from . import clients

PROFILE_KEYS = ("verified_income", "income_windows", "months_with_income", "income_variation", "hidden",
                "bills_on_time_rate", "salary_day", "emi_day")


def _lenders(s: dict) -> list[dict]:
    return s["profile"]["loans"] + [c for c in s["profile"]["cards"] if c.get("lender")]


def _rebuild(s: dict) -> None:
    cf = s["cashflow"]
    rows = clients.AccountAggregatorClient().fetch(s["user_id"], s["day"])
    p = cashflow.build_profile(rows, cf["labels"], _lenders(s), s["day"])
    cf["profile"] = p
    s["profile"]["cashflow"] = {k: p[k] for k in PROFILE_KEYS}


def read(s: dict) -> dict:
    uid = s["user_id"]
    rows = clients.AccountAggregatorClient().fetch(uid, s["day"])
    sources = sorted({r["source"] for r in rows})
    db.consent(uid, "Account Aggregator: share 6 months of bank statements",
               f"Accounts: {', '.join(x for x in sources if x != 'Paytm app')}; purpose: loan eligibility; valid 90 days")
    db.trace(uid, "event", "AA data fetched", f"{len(rows)} transactions from {len(sources)} sources: {', '.join(sources)}")

    labels, model = reader.classify(rows, s["persona"]["name"])
    s["cashflow"] = {"model": model, "labels": labels, "read_day": s["day"], "answers": {}}
    _rebuild(s)
    p = s["cashflow"]["profile"]

    truth = {r["id"]: r["truth"] for r in clients.AccountAggregatorClient().fetch(uid, s["day"], with_truth=True)}
    kw = {r["id"]: reader.keyword_label(r) for r in rows}
    s["cashflow"]["eval"] = {
        "reader": round(100 * sum(labels[i]["label"] == truth[i] for i in truth) / len(truth)),
        "keywords": round(100 * sum(kw[i] == truth[i] for i in truth) / len(truth)),
        "keyword_income": cashflow.keyword_income(rows, kw, s["day"]),
    }
    ev = s["cashflow"]["eval"]
    db.trace(uid, "reader", f"Reader ({model}) labelled {len(rows)} transactions",
             f"accuracy on these statements: reader {ev['reader']}%, keyword rules {ev['keywords']}%. Labels only, no amounts.")
    db.trace(uid, "rule", "Cash-flow profile built from labels",
             f"verified income {inr(p['verified_income'])}/month ({p['months_with_income']}/6 months, keyword rules found {inr(ev['keyword_income'])}); "
             f"bills on time {p['bills'] - p['bills_late']}/{p['bills']}; hidden debts {len(p['hidden'])}")
    for h in p["hidden"]:
        db.trace(uid, "guard", f"Debt not on bureau report: {h['name']}", f"{inr(h['monthly'])} in the last 30 days, counted in the EMI load")

    # Re-run the lender rules with the new evidence.
    app = s["application"]
    reasons, _ = engine.decode_reasons(s["profile"], app)
    offers, checks = engine.match_offers(s["profile"], app, reasons)
    for c in checks:
        db.trace(uid, "rule", f"offer {c['code']}: {'eligible' if c['passed'] else 'not eligible'}", c["expr"])
    s["reasons"] = reasons or s["reasons"]
    s["offers"] = offers
    s["plan"] = engine.build_plan(s["reasons"], s["profile"], app)
    db.trace(uid, "tool", "build_plan (with statement evidence)", f"{len(s['plan'])} actions: " + ", ".join(a["id"] for a in s["plan"]))
    return s


def refresh(s: dict) -> None:
    """New month of statements: label only the new rows, then rebuild the profile."""
    cf = s.get("cashflow")
    if not cf:
        return
    rows = clients.AccountAggregatorClient().fetch(s["user_id"], s["day"])
    new = [r for r in rows if r["id"] not in cf["labels"]]
    if new:
        labels, model = reader.classify(new, s["persona"]["name"])
        cf["labels"].update(labels)
        db.trace(s["user_id"], "reader", f"Reader ({model}) labelled {len(new)} new transactions", f"day {s['day']}")
    _rebuild(s)


def answer_gap(s: dict, gap: str, answer: str) -> None:
    s["cashflow"]["answers"][gap] = answer
    db.trace(s["user_id"], "event", f"Customer answered: {gap}", f"{answer} (self-declared, weighted lower than statement evidence)")


# ---------------------------------------------------------------- funding (rules, from the profile)

CUTTABLE = ("food_delivery", "shopping")


def funding(actions: list[dict], s: dict, lang: str) -> dict[str, dict]:
    """For each money-requiring action, how the customer can pay for it from their own cash flow."""
    cf = s.get("cashflow")
    if not cf:
        return {}
    p = cf["profile"]
    spare = max(0, p["surplus"])
    freed = sum(h["monthly"] for h in p["hidden"])
    cuts = {c: p["spend"].get(c, 0) // 2 for c in CUTTABLE}
    out = {}
    for a in actions:
        pay = a.get("paytm_action") or {}
        amount = pay.get("amount") or 0
        if not amount or a["done"]:
            continue
        months = max(1, round(a["due_day"] / 30))
        need = math.ceil(amount / months / 100) * 100
        parts, left = [], need
        for kind, avail in [("spare", spare), ("freed", freed if months > 1 else 0)] + [(f"cut.{c}", v) for c, v in cuts.items()]:
            take = min(avail, left)
            if take >= 100:
                key = "spare_once" if kind == "spare" and months == 1 else kind
                parts.append(t(lang, f"fund.{key}", amount=take))
                left -= take
                if kind == "spare":
                    spare -= take
                elif kind == "freed":
                    freed -= take
                else:
                    cuts[kind[4:]] -= take
            if left <= 0:
                break
        out[a["id"]] = {
            "title": t(lang, "fund.title", amount=need) if months > 1 else t(lang, "fund.title_once", amount=amount),
            "parts": parts,
            "covered": left <= 0,
        }
    return out


# ---------------------------------------------------------------- view

LABEL_EN = {
    "income_salary": "Salary", "income_gig": "Gig income", "loan_disbursal": "Borrowed", "self_transfer": "Own account",
    "transfer_family": "Family", "rent": "Rent", "emi": "EMI", "bnpl": "Pay later", "informal_loan": "Hand loan",
    "card_payment": "Card bill", "utility_bill": "Bill", "mobile_bill": "Mobile", "groceries": "Groceries",
    "food_delivery": "Food delivery", "fuel": "Fuel", "shopping": "Shopping", "cash_withdrawal": "Cash",
    "bank_charges": "Bank charge", "savings": "Savings", "other": "Other",
}


def view(s: dict, lang: str) -> dict | None:
    cf = s.get("cashflow")
    if not cf:
        return None
    p, ev = cf["profile"], cf["eval"]
    findings = [
        {"kind": "income", "text": t(lang, "find.income", amount=p["verified_income"], n=p["months_with_income"]),
         "sub": t(lang, "find.income_from", names=", ".join(list(p["income_sources"])[:3]))},
        {"kind": "bills", "text": t(lang, "find.bills", ok=p["bills"] - p["bills_late"], n=p["bills"])},
    ]
    for h in p["hidden"]:
        findings.append({"kind": "hidden", "text": t(lang, "find.hidden", name=h["name"], amount=h["monthly"])})
    for b in p["borrowed"]:
        findings.append({"kind": "borrowed", "text": t(lang, "find.borrowed", amount=b["amount"], name=b["from"], days=b["days_ago"])})
    if p["salary_day"] and p["emi_day"] and p["emi_day"] <= p["salary_day"]:
        findings.append({"kind": "timing", "text": t(lang, "find.timing", sal=p["salary_day"], due=p["emi_day"])})
    if p["spend"]:
        cat, amt = next(iter(p["spend"].items()))
        findings.append({"kind": "spend", "text": t(lang, "find.spend", cat=t(lang, f"cat.{cat}"), amount=amt)})

    gap = next((g for g in p["gaps"] if g not in cf["answers"]), None)
    rows = clients.AccountAggregatorClient().fetch(s["user_id"], s["day"])
    feed = [
        {"id": r["id"], "day": r["day"], "narration": r["narration"], "amount": r["amount"], "dir": r["dir"], "source": r["source"],
         "label": LABEL_EN[cf["labels"][r["id"]]["label"]], "keyword": LABEL_EN[reader.keyword_label(r)],
         "by": cf["labels"][r["id"]]["by"]}
        for r in sorted(rows, key=lambda r: -r["day"]) if r["id"] in cf["labels"]
    ][:60]
    return {
        "model": cf["model"],
        "rows": p["rows"],
        "sources": [{"name": k, "rows": v} for k, v in p["sources"].items()],
        "verified_income": p["verified_income"],
        "keyword_income": ev["keyword_income"],
        "accuracy": {"reader": ev["reader"], "keywords": ev["keywords"]},
        "findings": findings,
        "gap": {"id": gap, "question": t(lang, f"gap.{gap}.q"), "options": [t(lang, f"gap.{gap}.a1"), t(lang, f"gap.{gap}.a2")]} if gap else None,
        "feed": feed,
    }

"""Cash-flow profile: deterministic numbers built from the reader's labels. No LLM here.

Every figure comes from the raw amounts; the LLM only said what each transaction was.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from statistics import median

from ..agent.reader import INCOME, OBLIGATIONS

DISCRETIONARY = ["food_delivery", "shopping", "cash_withdrawal", "fuel", "groceries"]


def _key(name: str) -> str:
    words = re.findall(r"[a-z]+", name.lower())
    skip = {"ltd", "pvt", "limited", "the", "services", "serv", "india", "technologies", "finance", "financial"}
    words = [w for w in words if w not in skip] or words
    return words[0] if words else "unknown"


def _bureau_match(row: dict, counterparty: str, lenders: list[str]) -> str | None:
    text = (row["narration"] + " " + counterparty).lower()
    for lender in lenders:
        tokens = [t for t in re.findall(r"[a-z]+", lender.lower()) if len(t) >= 3 and t not in {"finance", "financial", "credit", "services"}]
        if tokens and all(t in text for t in tokens[:1]):
            return lender
    return None


def build_profile(rows: list[dict], labels: dict[str, dict], bureau_loans: list[dict], as_of: int) -> dict:
    """Profile of the last 6 months up to day `as_of`. Windows are 30 days, newest first."""
    rows = [r for r in rows if r["day"] <= as_of and r["id"] in labels]
    lab = {rid: v["label"] for rid, v in labels.items()}
    cp = {rid: v.get("counterparty") or "" for rid, v in labels.items()}
    lenders = [l.get("lender", l["name"]) for l in bureau_loans]

    # ---- income: 6 windows of 30 days
    windows = [0] * 6
    income_by_key: dict[str, int] = defaultdict(int)
    income_names: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r["dir"] == "in" and lab[r["id"]] in INCOME:
            k = (as_of - r["day"]) // 30
            if 0 <= k < 6:
                windows[k] += r["amount"]
                name = cp[r["id"]] or lab[r["id"]]
                group = _key(name)[:4]  # "Bundl Technologies" and "BUNDL TECH PVT LTD" are one payer
                income_by_key[group] += r["amount"]
                income_names[group][name] += 1
    income_sources = {
        max(income_names[g].items(), key=lambda x: x[1])[0]: amt
        for g, amt in sorted(income_by_key.items(), key=lambda x: -x[1])
    }
    months_with_income = sum(1 for w in windows if w > 0)
    verified_income = int(median(windows)) if months_with_income else 0
    mean = sum(windows) / 6
    variation = (max(windows) - min(windows)) / mean if mean else 0.0

    # ---- obligations in the last 30 days, split into bureau-known and hidden.
    # A debt whose latest payment the reader marked as closing (foreclosure, settle, purna) is over.
    closing = {rid for rid, v in labels.items() if v.get("closing")}
    last_payment: dict[str, dict] = {}
    for r in rows:
        if r["dir"] == "out" and lab[r["id"]] in OBLIGATIONS and not _bureau_match(r, cp[r["id"]], lenders):
            last_payment[_key(cp[r["id"]] or r["narration"])] = r
    closed = {k for k, r in last_payment.items() if r["id"] in closing}

    known: dict[str, int] = defaultdict(int)
    hidden: dict[str, dict] = {}
    for r in rows:
        if r["dir"] != "out" or lab[r["id"]] not in OBLIGATIONS or r["day"] <= as_of - 30:
            continue
        lender = _bureau_match(r, cp[r["id"]], lenders)
        if lender:
            known[lender] += r["amount"]
        else:
            k = _key(cp[r["id"]] or r["narration"])
            if k in closed:
                continue
            h = hidden.setdefault(k, {"key": k, "name": cp[r["id"]] or k.title(), "kind": lab[r["id"]], "monthly": 0, "payments": 0})
            h["monthly"] += r["amount"]
            h["payments"] += 1

    # ---- bills paid through Paytm with a due date
    bills = [r for r in rows if r.get("due_date") and r["day"] > as_of - 182]
    late = [r for r in bills if r["date"] > r["due_date"]]
    on_time_rate = (len(bills) - len(late)) / len(bills) if bills else 1.0

    # ---- salary day vs EMI day (only meaningful with salary income and a bureau loan)
    sal_days = [date.fromisoformat(r["date"]).day for r in rows if lab[r["id"]] == "income_salary" and r["day"] > as_of - 120]
    emi_rows = [r for r in rows if lab[r["id"]] == "emi" and r["day"] > as_of - 35 and _bureau_match(r, cp[r["id"]], lenders)
                and "overdue" not in r["narration"].lower()]
    salary_day = int(median(sal_days)) if sal_days else None
    emi_day = int(median(date.fromisoformat(r["date"]).day for r in emi_rows)) if emi_rows else None
    bounces = [r for r in rows if lab[r["id"]] == "bank_charges" and r["day"] > as_of - 182]

    # ---- spending, average per 30 days over the last 90
    spend: dict[str, int] = defaultdict(int)
    total_out = 0
    for r in rows:
        if r["dir"] == "out" and r["day"] > as_of - 90:
            if lab[r["id"]] in DISCRETIONARY:
                spend[lab[r["id"]]] += r["amount"]
            if lab[r["id"]] not in {"self_transfer", "savings"}:
                total_out += r["amount"]
    spend = {k: round(v / 3) for k, v in sorted(spend.items(), key=lambda x: -x[1])}
    surplus = verified_income - round(total_out / 3)

    borrowed = [r for r in rows if lab[r["id"]] == "loan_disbursal" and r["day"] > as_of - 60]
    gaps = []
    if not any(lab[r["id"]] == "rent" for r in rows):
        gaps.append("rent")

    sources: dict[str, int] = defaultdict(int)
    for r in rows:
        sources[r["source"]] += 1

    return {
        "as_of": as_of,
        "rows": len(rows),
        "sources": dict(sources),
        "verified_income": verified_income,
        "income_windows": windows[::-1],
        "months_with_income": months_with_income,
        "income_variation": round(variation, 2),
        "income_sources": dict(sorted(income_sources.items(), key=lambda x: -x[1])[:4]),
        "known_obligations": dict(known),
        "hidden": sorted(hidden.values(), key=lambda h: -h["monthly"]),
        "bills": len(bills),
        "bills_late": len(late),
        "bills_on_time_rate": round(on_time_rate, 2),
        "salary_day": salary_day,
        "emi_day": emi_day,
        "bounces": len(bounces),
        "spend": spend,
        "surplus": surplus,
        "borrowed": [{"amount": r["amount"], "from": cp[r["id"]] or "loan app", "days_ago": as_of - r["day"]} for r in borrowed],
        "gaps": gaps,
    }


def keyword_income(rows: list[dict], kw_labels: dict[str, str], as_of: int) -> int:
    """Monthly income a keyword rule set would find, for the 'why an LLM' comparison."""
    windows = [0] * 6
    for r in rows:
        if r["day"] <= as_of and r["dir"] == "in" and kw_labels.get(r["id"]) in INCOME:
            k = (as_of - r["day"]) // 30
            if 0 <= k < 6:
                windows[k] += r["amount"]
    return int(median(windows))

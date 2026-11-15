"""Deterministic rules engine. No LLM in this file.

decode_reasons  -> why the lender said no (with the numbers as evidence)
match_offers    -> what the user qualifies for today
build_plan      -> actions with measurable targets, computed from the user's data
check_progress  -> progress per action, readiness, and whether the user is now eligible
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_DIR = Path(__file__).parent
TH: dict[str, Any] = yaml.safe_load((_DIR / "thresholds.yaml").read_text(encoding="utf-8"))
PRODUCTS: dict[str, Any] = yaml.safe_load((_DIR / "products.yaml").read_text(encoding="utf-8"))


def emi(principal: float, annual_rate: float, months: int) -> int:
    r = annual_rate / 12
    if r == 0:
        return round(principal / months)
    f = (1 + r) ** months
    return round(principal * r * f / (f - 1))


def metrics(profile: dict, application: dict) -> dict:
    """All derived numbers the rules look at."""
    cf = profile.get("cashflow") or {}
    # Once statements are read, verified income replaces declared income,
    # and debts found in the statements but missing from the bureau count too.
    income = cf.get("verified_income") or profile["monthly_income"]
    hidden_emi = sum(h["monthly"] for h in cf.get("hidden", []))
    existing_emi = sum(l["emi"] for l in profile["loans"]) + hidden_emi
    proposed_emi = emi(application["amount"], TH["pricing"]["personal_loan_rate"], application["tenure_months"])
    limit = sum(c["limit"] for c in profile["cards"] if not c.get("secured"))
    balance = sum(c["balance"] for c in profile["cards"] if not c.get("secured"))
    inflow = cf.get("income_windows") or profile.get("inflow_6m") or [income]
    mean = sum(inflow) / len(inflow)
    return {
        "income": income,
        "existing_emi": existing_emi,
        "hidden_emi": hidden_emi,
        "proposed_emi": proposed_emi,
        "foir": (existing_emi + proposed_emi) / income,
        "emi_share": proposed_emi / income,
        "card_limit": limit,
        "card_balance": balance,
        "utilisation": (balance / limit) if limit else 0.0,
        "income_variation": (max(inflow) - min(inflow)) / mean if mean else 0.0,
    }


def pct(x: float) -> int:
    return round(x * 100)


def decode_reasons(profile: dict, application: dict) -> tuple[list[dict], list[dict]]:
    """Returns (reasons, checks). checks lists every rule evaluated, pass or fail, for the audit trail."""
    m = metrics(profile, application)
    reasons: list[dict] = []
    checks: list[dict] = []

    def rule(code: str, failed: bool, expr: str, evidence: dict) -> None:
        checks.append({"code": code, "passed": not failed, "expr": expr})
        if failed:
            reasons.append({"code": code, "evidence": evidence})

    need = TH["thin_file"]["min_on_time_cycles"]
    rule(
        "THIN_FILE",
        profile["on_time_cycles"] < need,
        f"on-time cycles {profile['on_time_cycles']} >= {need}",
        {"have": profile["on_time_cycles"], "need": need},
    )

    min_score = TH["low_score"]["min_score"]
    score = profile.get("score")
    rule(
        "LOW_SCORE",
        score is not None and score < min_score,
        f"score {score if score is not None else 'none'} >= {min_score}",
        {"score": score, "min": min_score},
    )

    max_foir = TH["foir"]["max"]
    rule(
        "HIGH_FOIR",
        m["foir"] > max_foir,
        f"EMI load {pct(m['foir'])}% <= {pct(max_foir)}%",
        {
            "foir": pct(m["foir"]),
            "max": pct(max_foir),
            "income": m["income"],
            "existing_emi": m["existing_emi"],
            "proposed_emi": m["proposed_emi"],
        },
    )

    max_util = TH["utilisation"]["max"]
    rule(
        "HIGH_UTILISATION",
        m["utilisation"] > max_util,
        f"card use {pct(m['utilisation'])}% <= {pct(max_util)}%",
        {"util": pct(m["utilisation"]), "max": pct(max_util), "bal": m["card_balance"], "limit": m["card_limit"]},
    )

    need_clean = TH["dpd"]["min_clean_cycles"]
    clean = profile.get("clean_cycles_since_dpd")
    dpd = profile.get("last_dpd")
    rule(
        "RECENT_DPD",
        dpd is not None and (clean or 0) < need_clean,
        f"on-time EMIs since last miss {clean if dpd else 'n/a'} >= {need_clean}",
        {"loan": (dpd or {}).get("loan", ""), "have": clean or 0, "need": need_clean},
    )

    max_enq = TH["enquiries"]["max_30d"]
    rule(
        "ENQUIRY_SPIKE",
        profile["enquiries_30d"] > max_enq,
        f"enquiries in 30 days {profile['enquiries_30d']} <= {max_enq}",
        {"n": profile["enquiries_30d"], "max": max_enq},
    )

    max_share = TH["income"]["max_emi_share"]
    rule(
        "INCOME_LOW",
        m["emi_share"] > max_share,
        f"new EMI share {pct(m['emi_share'])}% <= {pct(max_share)}%",
        {"emi": m["proposed_emi"], "share": pct(m["emi_share"]), "max": pct(max_share), "income": m["income"]},
    )

    max_var = TH["income"]["max_variation"]
    rule(
        "INCOME_UNSTABLE",
        m["income_variation"] > max_var,
        f"income variation {pct(m['income_variation'])}% <= {pct(max_var)}%",
        {"var": pct(m["income_variation"]), "max": pct(max_var)},
    )
    return reasons, checks


def match_offers(profile: dict, application: dict, reasons: list[dict]) -> tuple[list[dict], list[dict]]:
    """Runs every product through its eligibility rule. Returns (offers, checks)."""
    codes = {r["code"] for r in reasons}
    m = metrics(profile, application)
    offers: list[dict] = []
    checks: list[dict] = []

    # FD-backed card: for people blocked on history or repayment record.
    fd = PRODUCTS["fd_card"]
    fd_ok = bool(codes & set(fd["for_reasons"])) and not profile.get("fd_card_active")
    checks.append({"code": "fd_card", "passed": fd_ok, "expr": "blocked on history or repayment record, no FD card yet"})
    if fd_ok:
        offers.append(
            {
                "id": "fd_card",
                "fd_amount": fd["fd_amount"],
                "limit": round(fd["fd_amount"] * fd["limit_ratio"]),
                "fd_rate": fd["fd_rate"],
            }
        )

    # Smaller loan: largest amount that passes score, repayment and EMI-load rules.
    sl = PRODUCTS["small_loan"]
    score = profile.get("score")
    score_ok = score is not None and score >= sl["min_score"]
    dpd_ok = not (sl["require_no_recent_dpd"] and "RECENT_DPD" in codes)
    chosen = None
    if score_ok and dpd_ok and "THIN_FILE" not in codes:
        for amount in sl["amounts"]:
            if amount > application["amount"] * sl["max_share_of_request"]:
                continue
            e = emi(amount, sl["rate"], sl["tenure_months"])
            foir = (m["existing_emi"] + e) / m["income"]
            if foir <= sl["max_foir"]:
                chosen = {
                    "id": "small_loan",
                    "amount": amount,
                    "emi": e,
                    "rate": sl["rate"],
                    "tenure_months": sl["tenure_months"],
                    "foir": pct(foir),
                    "max_foir": pct(sl["max_foir"]),
                }
                break
    checks.append(
        {
            "code": "small_loan",
            "passed": chosen is not None,
            "expr": f"score >= {sl['min_score']}, no recent missed EMI, EMI load <= {pct(sl['max_foir'])}%",
        }
    )
    if chosen:
        offers.insert(0, chosen)

    # Cash-flow loan: for steady earners the bureau cannot score, decided on verified statements.
    cf = profile.get("cashflow")
    cl = PRODUCTS["cashflow_loan"]
    if cf:
        cap = min(application["amount"] * cl["max_share_of_request"], cf["verified_income"] * cl["max_income_multiple"])
        basics = (
            cf["months_with_income"] >= cl["min_months_income"]
            and cf["income_variation"] <= cl["max_income_variation"]
            and cf["bills_on_time_rate"] >= cl["min_bills_on_time"]
            and not (cl["require_no_recent_dpd"] and "RECENT_DPD" in codes)
        )
        picked = None
        if basics:
            for amount in cl["amounts"]:
                if amount > cap:
                    continue
                e = emi(amount, cl["rate"], cl["tenure_months"])
                foir = (m["existing_emi"] + e) / m["income"]
                if foir <= cl["max_foir"]:
                    picked = {
                        "id": "cashflow_loan", "amount": amount, "emi": e, "rate": cl["rate"],
                        "tenure_months": cl["tenure_months"], "foir": pct(foir), "max_foir": pct(cl["max_foir"]),
                        "income": cf["verified_income"], "months": cf["months_with_income"],
                    }
                    break
        checks.append({
            "code": "cashflow_loan",
            "passed": picked is not None,
            "expr": f"income in {cf['months_with_income']}/6 months >= {cl['min_months_income']}, variation {pct(cf['income_variation'])}% <= {pct(cl['max_income_variation'])}%, "
                    f"bills on time {pct(cf['bills_on_time_rate'])}% >= {pct(cl['min_bills_on_time'])}%, EMI load incl. hidden debts <= {pct(cl['max_foir'])}%",
        })
        if picked:
            offers.insert(0, picked)
    return offers, checks


def _metric(profile: dict, application: dict, name: str) -> float:
    m = metrics(profile, application)
    if name == "fd_card_active":
        return 1 if profile.get("fd_card_active") else 0
    if name == "on_time_cycles":
        return profile["on_time_cycles"]
    if name == "bill_autopay":
        return 1 if any(b["autopay"] for b in profile["bills"]) else 0
    if name == "utilisation":
        return pct(m["utilisation"])
    if name == "foir":
        return pct(m["foir"])
    if name == "emi_autopay":
        loans = [l for l in profile["loans"] if l["emi"] > 0]
        return 1 if loans and all(l["autopay"] for l in loans) else 0
    if name == "clean_cycles":
        return profile.get("clean_cycles_since_dpd") or 0
    if name == "enquiries_30d":
        return profile["enquiries_30d"]
    if name == "score":
        return profile.get("score") or 0
    cf = profile.get("cashflow") or {}
    if name.startswith("hidden:"):
        return next((h["monthly"] for h in cf.get("hidden", []) if h["key"] == name[7:]), 0)
    if name == "emi_after_salary":
        return 1 if cf.get("emi_day") and cf.get("salary_day") and cf["emi_day"] > cf["salary_day"] else 0
    return 0


def build_plan(reasons: list[dict], profile: dict, application: dict) -> list[dict]:
    """One or two actions per reason. Start and target values come from the user's own data."""
    m = metrics(profile, application)
    actions: list[dict] = []

    def add(aid: str, code: str, metric: str, target: float, due: int, params: dict | None = None, pay: dict | None = None, tkey: str | None = None):
        actions.append(
            {
                "id": aid,
                "tkey": tkey or aid,
                "reason_code": code,
                "metric": metric,
                "start": _metric(profile, application, metric),
                "target": target,
                "due_day": due,
                "params": params or {},
                "paytm_action": pay,
            }
        )

    for r in reasons:
        code, ev = r["code"], r["evidence"]
        if code == "THIN_FILE":
            fd = PRODUCTS["fd_card"]
            add(
                "open_fd_card", code, "fd_card_active", 1, 7,
                {"amount": fd["fd_amount"], "limit": round(fd["fd_amount"] * fd["limit_ratio"])},
                {"type": "open_fd", "amount": fd["fd_amount"]},
            )
            add("card_cycles", code, "on_time_cycles", ev["need"], 90, {"target": ev["need"]})
            late = next((b for b in profile["bills"] if not b["autopay"]), None)
            if late:
                add("bill_autopay", code, "bill_autopay", 1, 30, {"biller": late["biller"]}, {"type": "autopay", "amount": 0})
        elif code == "HIGH_UTILISATION":
            target = TH["utilisation"]["target"]
            amount = max(0, round(m["card_balance"] - target * m["card_limit"]))
            add(
                "reduce_util", code, "utilisation", pct(target), 90,
                {"start": ev["util"], "target": pct(target), "amount": amount},
                {"type": "pay_card", "amount": amount},
            )
        elif code == "HIGH_FOIR":
            limit_ = TH["foir"]["max"]
            remaining = m["existing_emi"]
            # 1. Debts found in the statements but missing from the bureau: clear them first.
            for h in (profile.get("cashflow") or {}).get("hidden", []):
                add(f"clear_{h['key']}", code, f"hidden:{h['key']}", 0, 60,
                    {"name": h["name"], "monthly": h["monthly"]}, {"type": "clear_debt", "amount": 0}, tkey="clear_hidden")
                remaining -= h["monthly"]
            # 2. Then close the smallest bureau loans until the EMI load fits.
            for l in sorted((l for l in profile["loans"] if l["emi"] > 0), key=lambda l: l["outstanding"]):
                if (remaining + m["proposed_emi"]) / m["income"] <= limit_:
                    break
                remaining -= l["emi"]
                after = (remaining + m["proposed_emi"]) / m["income"]
                add(
                    f"close_{l['id']}", code, "foir", pct(limit_), 90,
                    {"loan": l["name"], "amount": l["outstanding"], "emi": l["emi"], "max": pct(limit_), "after": pct(after)},
                    {"type": "close_loan", "amount": l["outstanding"]}, tkey="close_loan",
                )
        elif code == "RECENT_DPD":
            cf = profile.get("cashflow") or {}
            if cf.get("salary_day") and cf.get("emi_day") and cf["emi_day"] <= cf["salary_day"]:
                # The statements show the EMI is taken before salary arrives: a timing problem, not a money problem.
                add("move_emi_date", code, "emi_after_salary", 1, 30,
                    {"loan": ev["loan"], "emi_day": cf["emi_day"], "salary_day": cf["salary_day"], "new_day": min(28, cf["salary_day"] + 3)},
                    {"type": "emi_date", "amount": 0})
            add("emi_autopay", code, "emi_autopay", 1, 7, {"loan": ev["loan"]}, {"type": "autopay", "amount": 0})
            add("clean_cycles", code, "clean_cycles", ev["need"], 90, {"target": ev["need"]})
        elif code == "ENQUIRY_SPIKE":
            add("no_enquiries", code, "enquiries_30d", ev["max"], 30, {"n": ev["n"]})
        elif code == "LOW_SCORE":
            add("raise_score", code, "score", ev["min"], 90, {"start": ev["score"], "target": ev["min"]})
        elif code == "INCOME_LOW":
            add("lower_amount", code, "score", 0, 0, {"emi": ev["emi"], "max": ev["max"]})
        elif code == "INCOME_UNSTABLE":
            add("steady_income", code, "score", 0, 90, {})
    return actions


def _progress(start: float, current: float, target: float) -> float:
    if start == target:
        return 1.0
    p = (current - start) / (target - start)
    return max(0.0, min(1.0, p))


def check_progress(plan: list[dict], profile: dict, application: dict) -> dict:
    """Recomputes every action from current data, then re-runs the lender rules."""
    out = []
    for a in plan:
        current = _metric(profile, application, a["metric"])
        down = a["target"] < a["start"]
        done = current <= a["target"] if down else current >= a["target"]
        p = 1.0 if done else _progress(a["start"], current, a["target"])
        out.append({**a, "current": current, "progress": round(p, 2), "done": done})
    reasons, checks = decode_reasons(profile, application)
    readiness = round(100 * sum(a["progress"] for a in out) / len(out)) if out else 100
    eligible = not reasons
    if eligible:
        readiness = 100
    return {
        "actions": out,
        "readiness": readiness,
        "eligible": eligible,
        "open_reasons": [r["code"] for r in reasons],
        "checks": checks,
    }

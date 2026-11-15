"""Adapters for the three outside systems. Today they read the mock; a real integration
replaces the body of each method and nothing else changes."""
from __future__ import annotations

import json

from .. import db
from ..config import DATA_DIR
from ..rules import engine

TX_DIR = DATA_DIR / "transactions"


class LenderClient:
    """Partner lender decision API (mocked: applies the published policy in thresholds.yaml)."""

    def apply(self, user_id: str, profile: dict, application: dict) -> dict:
        reasons, _ = engine.decode_reasons(profile, application)
        return {
            "decision": "REJECTED" if reasons else "APPROVED",
            "reason_codes": [r["code"] for r in reasons],
            "reference": f"LN-{user_id.upper()}-{application['amount'] // 1000}K",
        }


class BureauClient:
    """Credit bureau report, pulled with the user's consent (mocked)."""

    def report(self, user_id: str) -> dict:
        p = (db.get_state(user_id) or {}).get("profile", {})
        return {
            "score": p.get("score"),
            "on_time_cycles": p.get("on_time_cycles", 0),
            "accounts": len(p.get("loans", [])) + len(p.get("cards", [])),
            "enquiries_30d": p.get("enquiries_30d", 0),
            "last_dpd": p.get("last_dpd"),
            "loans": p.get("loans", []),
            "cards": p.get("cards", []),
        }


class AccountAggregatorClient:
    """Bank statements shared with consent through RBI's Account Aggregator framework (mocked).
    Covers every linked bank account, whichever UPI app made the payment, plus Paytm app records.
    `truth` is the hand label used only to score the reader; it is never sent to the LLM."""

    _cache: dict[str, list[dict]] = {}

    def fetch(self, user_id: str, as_of_day: int, with_truth: bool = False) -> list[dict]:
        if user_id not in self._cache:
            path = TX_DIR / f"{user_id}.json"
            self._cache[user_id] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        rows = [r for r in self._cache[user_id] if r["day"] <= as_of_day]
        if with_truth:
            return rows
        return [{k: v for k, v in r.items() if k != "truth"} for r in rows]


class PaytmClient:
    """The user's Paytm activity: bills, UPI inflow, EMI mandates (mocked)."""

    def summary(self, user_id: str) -> dict:
        p = (db.get_state(user_id) or {}).get("profile", {})
        return {
            "bills": len(p.get("bills", [])),
            "emis": len(p.get("loans", [])),
            "inflow_6m": p.get("inflow_6m", []),
        }

    def transactions(self, user_id: str) -> list[dict]:
        return (db.get_state(user_id) or {}).get("feed", [])

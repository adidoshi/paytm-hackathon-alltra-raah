"""Adapters for the three outside systems. Today they read the mock; a real integration
replaces the body of each method and nothing else changes."""
from __future__ import annotations

from .. import db
from ..rules import engine


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

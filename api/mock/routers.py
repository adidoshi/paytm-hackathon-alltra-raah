"""Mocked outside systems, exposed over HTTP so they can be inspected and later swapped for real ones."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import clients, journey

router = APIRouter(prefix="/mock", tags=["mock"])


class LenderApply(BaseModel):
    user_id: str
    amount: int | None = None
    tenure_months: int | None = None


def _state(user_id: str) -> dict:
    try:
        return journey.state_of(user_id)
    except KeyError:
        raise HTTPException(404, "unknown user")


@router.post("/lender/apply")
def lender_apply(body: LenderApply):
    s = _state(body.user_id)
    app = {**s["application"]}
    if body.amount:
        app["amount"] = body.amount
    if body.tenure_months:
        app["tenure_months"] = body.tenure_months
    return clients.LenderClient().apply(body.user_id, s["profile"], app)


@router.get("/bureau/report/{user_id}")
def bureau_report(user_id: str):
    _state(user_id)
    return clients.BureauClient().report(user_id)


@router.get("/aa/{user_id}/statements")
def aa_statements(user_id: str, as_of_day: int = 0):
    """Account Aggregator financial information (mocked): all linked bank accounts."""
    _state(user_id)
    return {"transactions": clients.AccountAggregatorClient().fetch(user_id, as_of_day)}


@router.get("/paytm/{user_id}/transactions")
def paytm_transactions(user_id: str):
    s = _state(user_id)
    return {"bills": s["profile"]["bills"], "inflow_6m": s["profile"]["inflow_6m"], "transactions": s["feed"]}

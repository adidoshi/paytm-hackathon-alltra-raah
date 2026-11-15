"""The cash-flow reader: an LLM reads raw bank-statement and Paytm narrations and labels them.

The LLM returns, per transaction id, only a label from a fixed list and a counterparty name.
It never returns amounts: every total is computed in code from these labels.
Order of attempts: Sarvam-105B, then Gemini, then the keyword baseline.
"""
from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor

from .. import config
from ..services import sarvam
from . import llm

LABELS = {
    "income_salary": "salary from an employer (any wording, e.g. SAL, pagaar, from a shop or company)",
    "income_gig": "payout from a gig or delivery platform (Swiggy = Bundl Technologies, Zomato, Rapido = Roppen Transportation, Uber, Zepto, Dunzo)",
    "loan_disbursal": "money received from a lender or loan app; this is borrowed money, not income",
    "self_transfer": "money moved between the customer's own accounts (the counterparty is the customer's own name, even if spelled slightly differently)",
    "transfer_family": "money sent to or received from family (aai, ammi, papa, bhai and similar, or a personal note)",
    "rent": "house or room rent paid to a person (e.g. bhade, kiraya, flat number in the note)",
    "emi": "loan EMI or repayment to a bank, NBFC or loan app (ACH debits to a finance company, overdue payments)",
    "bnpl": "buy-now-pay-later bill or EMI (LazyPay, Simpl, Slice, ZestMoney, Amazon Pay Later)",
    "informal_loan": "repayment to a private moneylender or hand loan (hapta, weekly fixed amount to a person or small enterprise)",
    "card_payment": "credit card bill payment, including ACH or autopay debits for a card (CC, CRD, CARD in the narration)",
    "utility_bill": "electricity, water or gas bill",
    "mobile_bill": "mobile recharge or postpaid bill",
    "groceries": "kirana, general store, supermarket or quick-commerce groceries (Blinkit = Blink Commerce, DMart, Zepto)",
    "food_delivery": "food ordered from Swiggy, Zomato or a restaurant (money going out)",
    "fuel": "petrol or diesel",
    "shopping": "online or retail shopping (Amazon, Myntra, Flipkart)",
    "cash_withdrawal": "ATM or cash withdrawal",
    "bank_charges": "bank fees, bounce or return charges",
    "savings": "fixed deposit, recurring deposit, SIP or other savings",
    "other": "anything that fits none of the above",
}
OBLIGATIONS = {"emi", "bnpl", "informal_loan"}
INCOME = {"income_salary", "income_gig"}

PROMPT = """You label Indian bank-statement and Paytm transactions for a lender's cash-flow review.
Narrations are raw: UPI/IMPS/NEFT/ACH strings, legal company names instead of brand names, Hindi and Marathi words in Latin script.
Use the direction: "in" is money received, "out" is money paid.

Labels:
{labels}

Return only a JSON array, one object per input row, in the same order:
[{{"id": "<id>", "label": "<one label from the list>", "counterparty": "<short readable name of the other party>", "closing": <true|false>}}]
"counterparty" is the other party's name copied as written in the narration, cleaned of codes and handles (for example "CITIUSTECH LIMITED" becomes "Citiustech Limited"); do not correct or guess the spelling.
"closing" is true only when the note says this payment ends or settles the debt (e.g. foreclosure, settle, full and final, purna, poora, band).
No amounts, no explanations, no markdown."""


def _prompt() -> str:
    return PROMPT.format(labels="\n".join(f"- {k}: {v}" for k, v in LABELS.items()))


def _rows_for_llm(rows: list[dict], customer: str = "") -> str:
    head = f"Customer name: {customer}\n" if customer else ""
    return head + "\n".join(json.dumps({"id": r["id"], "dir": r["dir"], "narration": r["narration"], "source": r["source"]}, ensure_ascii=False) for r in rows)


def _parse(text: str, ids: set[str]) -> dict[str, dict]:
    """Keep only known ids and allowed labels. Anything else is dropped."""
    m = re.search(r"\[.*\]", text or "", re.S)
    if not m:
        return {}
    try:
        items = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    out = {}
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        rid, label = str(it.get("id", "")), str(it.get("label", "")).strip()
        if rid in ids and label in LABELS:
            out[rid] = {"label": label, "counterparty": str(it.get("counterparty") or "")[:40], "closing": it.get("closing") is True}
    return out


def _cache_path(provider: str, chunk: list[dict], customer: str):
    key = hashlib.sha256((provider + _prompt() + _rows_for_llm(chunk, customer)).encode("utf-8")).hexdigest()[:24]
    return config.LLM_CACHE_DIR / f"reader-{provider}-{key}.json"


def _classify_chunk(provider: str, chunk: list[dict], customer: str) -> dict[str, dict]:
    path = _cache_path(provider, chunk, customer)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    ids = {r["id"] for r in chunk}
    if provider not in llm.providers():  # no key: saved answers only
        return {}
    if provider == "sarvam":
        text = sarvam.chat(_prompt(), _rows_for_llm(chunk, customer), max_tokens=4000, cache=False)
    else:
        text = llm.gemini_text(_prompt(), _rows_for_llm(chunk, customer))
    out = _parse(text or "", ids)
    if len(out) >= 0.8 * len(chunk):  # only cache a usable answer
        config.LLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def classify(rows: list[dict], customer: str = "", chunk_size: int = 30) -> tuple[dict[str, dict], str]:
    """Label every row. Returns ({id: {label, counterparty, by}}, main model name)."""
    if not rows:
        return {}, "none"
    chunks = [rows[i:i + chunk_size] for i in range(0, len(rows), chunk_size)]
    labels: dict[str, dict] = {}
    used = "keyword rules"
    # Saved answers from a model are used even when its key is missing (offline demo, tests).
    order = llm.providers() + [p for p in ("sarvam", "gemini") if p not in llm.providers()]
    for provider in order:
        todo = [c for c in chunks if any(r["id"] not in labels for r in c)]
        if not todo:
            break
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda c: _classify_chunk(provider, c, customer), todo))
        got = 0
        for res in results:
            for rid, v in res.items():
                if rid not in labels:
                    labels[rid] = {**v, "by": llm.model_name(provider)}
                    got += 1
        if got and used == "keyword rules":
            used = llm.model_name(provider)
    for r in rows:  # whatever the models missed
        if r["id"] not in labels:
            labels[r["id"]] = {"label": keyword_label(r), "counterparty": "", "by": "keyword rules"}
    return labels, used


# ----------------------------------------------------------------------- baseline

_KEYWORDS = [
    ("income_salary", ["salary", "sal "]),
    ("income_gig", ["payout"]),
    ("self_transfer", ["self"]),
    ("rent", ["rent"]),
    ("bnpl", ["lazypay", "simpl", "slice"]),
    ("emi", ["emi", "ach d-", "loan"]),
    ("card_payment", ["cc ", "credit card"]),
    ("utility_bill", ["electricity", "msedcl", "water bill"]),
    ("mobile_bill", ["recharge", "postpaid"]),
    ("food_delivery", ["swiggy", "zomato"]),
    ("groceries", ["kirana", "dmart", "grocery", "store"]),
    ("fuel", ["petrol", "fuel", "hpcl", "iocl", "bpcl"]),
    ("shopping", ["amazon", "myntra", "flipkart"]),
    ("cash_withdrawal", ["atm"]),
    ("bank_charges", ["chgs", "charges"]),
    ("savings", ["fd ", "fixed deposit"]),
]


def keyword_label(row: dict) -> str:
    """What a conventional keyword rule set makes of the narration."""
    text = row["narration"].lower() + " "
    for label, words in _KEYWORDS:
        if any(w in text for w in words):
            return label
    return "other"


def accuracy(rows: list[dict], labels: dict[str, str]) -> float:
    scored = [r for r in rows if "truth" in r]
    if not scored:
        return 0.0
    return sum(labels.get(r["id"]) == r["truth"] for r in scored) / len(scored)

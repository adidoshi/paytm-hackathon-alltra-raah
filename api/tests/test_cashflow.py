"""Statement reading: reader quality, profile numbers, offers and plans built on the evidence.

Runs offline: the reader uses the saved Sarvam-105B answers in api/data/llm_cache
(re-create them with `python -m api.scripts.pregen` after changing the prompt or data).
"""
import os
import tempfile

os.environ["RAAH_DB"] = os.path.join(tempfile.mkdtemp(), "test_cf.db")
os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""
os.environ["SARVAM_API_KEY"] = ""
os.environ["SARVAM_MCP"] = "0"

import pytest  # noqa: E402

from api import config, db  # noqa: E402
from api.agent import llm, reader  # noqa: E402
from api.rules import cashflow  # noqa: E402
from api.services import clients, journey  # noqa: E402


@pytest.fixture(autouse=True)
def clean():
    llm.get_llm.cache_clear()
    db.init()
    journey.reset()


def read(uid):
    journey.apply(uid, None, None, "en")
    s = journey.read_statements(uid)
    return s, journey.view(s, "en", lazy_explain=False)


@pytest.mark.parametrize("uid", ["ravi", "priya", "sameer"])
def test_reader_beats_keyword_rules(uid):
    # Label the rows the way the app does: the 6 months at consent, then each new month.
    s, _ = read(uid)
    for _ in range(3):
        s = journey.advance(uid)
    labels = s["cashflow"]["labels"]
    rows = clients.AccountAggregatorClient().fetch(uid, 90, with_truth=True)
    assert all(v["by"] != "keyword rules" for v in labels.values()), "saved reader answers are missing: run python -m api.scripts.pregen"
    llm_acc = reader.accuracy(rows, {k: v["label"] for k, v in labels.items()})
    kw_acc = reader.accuracy(rows, {r["id"]: reader.keyword_label(r) for r in rows})
    assert llm_acc >= 0.95 and llm_acc - kw_acc >= 0.2


def test_truth_never_reaches_the_reader():
    rows = clients.AccountAggregatorClient().fetch("priya", 0)
    assert rows and all("truth" not in r for r in rows)
    assert "truth" not in reader._rows_for_llm(rows)


def test_ravi_gets_a_cash_flow_loan_today():
    s, v = read("ravi")
    cf = v["cashflow"]
    assert cf["verified_income"] > cf["keyword_income"] + 5000  # Bundl / Roppen payouts are invisible to keywords
    offer = v["offers"][0]
    assert offer["id"] == "cashflow_loan" and "₹40,000" in offer["name"]


def test_priya_hidden_debts_are_found_and_counted():
    before = journey.view(journey.apply("priya", None, None, "en"), "en", lazy_explain=False)
    s, v = read("priya")
    names = {h["key"] for h in s["cashflow"]["profile"]["hidden"]}
    assert names == {"laxmi", "simpl"}
    assert v["snapshot"]["foir"] > before["snapshot"]["foir"]
    # the honest consequence: a smaller offer than before the statements were read
    assert "₹75,000" in before["offers"][0]["name"] and "₹50,000" in v["offers"][0]["name"]
    ids = [a["id"] for a in v["plan"]["actions"]]
    assert ids[:2] == ["clear_laxmi", "clear_simpl"]
    util = next(a for a in v["plan"]["actions"] if a["id"] == "reduce_util")
    assert util["funding"]["covered"] and len(util["funding"]["parts"]) >= 3


def test_sameer_timing_problem_and_borrowed_money():
    s, v = read("sameer")
    p = s["cashflow"]["profile"]
    assert p["verified_income"] == 32000 and v["cashflow"]["keyword_income"] == 0
    assert p["salary_day"] > p["emi_day"]
    assert p["borrowed"] and p["borrowed"][0]["amount"] == 5000
    assert v["plan"]["actions"][0]["id"] == "move_emi_date"
    assert v["cashflow"]["gap"]["id"] == "rent"
    s = journey.answer_gap("sameer", "rent", "Family home, no rent")
    assert journey.view(s, "en", lazy_explain=False)["cashflow"]["gap"] is None


@pytest.mark.parametrize("uid", ["ravi", "priya", "sameer"])
def test_statement_journey_still_reaches_approval_at_day_90(uid):
    read(uid)
    readiness = []
    for day in (30, 60, 90):
        s = journey.advance(uid)
        readiness.append(journey.view(s, "en", lazy_explain=False)["plan"]["readiness"])
        assert (s["status"] == "eligible") == (day == 90), f"{uid} day {day}"
    assert readiness == sorted(readiness)
    assert journey.reapply(uid, True)["status"] == "approved"


def test_settled_debt_stops_counting():
    s, _ = read("priya")
    journey.advance("priya")
    s = journey.advance("priya")  # Laxmi "hapta purna" and Simpl "settle all" land in this month
    assert s["cashflow"]["profile"]["hidden"] == []


def test_reader_output_is_filtered():
    text = '[{"id": "R001", "label": "income_gig"}, {"id": "R999", "label": "rent"}, {"id": "R002", "label": "lottery", "amount": 500000}]'
    out = reader._parse(text, {"R001", "R002"})
    assert set(out) == {"R001"} and "amount" not in out["R001"]


def test_no_keys_and_no_saved_answers_falls_back_to_keywords(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LLM_CACHE_DIR", tmp_path)
    rows = clients.AccountAggregatorClient().fetch("sameer", 0)
    labels, model = reader.classify(rows, "Sameer Shaikh")
    assert model == "keyword rules" and len(labels) == len(rows)


def test_profile_math_is_deterministic():
    rows = clients.AccountAggregatorClient().fetch("priya", 0, with_truth=True)
    truth = {r["id"]: {"label": r["truth"], "counterparty": r["narration"].split("/")[3] if r["narration"].startswith("UPI") else ""} for r in rows}
    p = cashflow.build_profile(rows, truth, journey._fresh("priya")["profile"]["loans"], 0)
    assert p["verified_income"] == 45000 and p["months_with_income"] == 6
    assert sum(h["monthly"] for h in p["hidden"] if h["key"] == "laxmi") == 700 * sum(
        1 for r in rows if r["truth"] == "informal_loan" and r["day"] > -30)

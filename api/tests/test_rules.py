import os
import tempfile

os.environ["RAAH_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""

import pytest  # noqa: E402

from api import db  # noqa: E402
from api.agent import llm  # noqa: E402
from api.rules.i18n import inr  # noqa: E402
from api.services import journey  # noqa: E402


@pytest.fixture(autouse=True)
def clean():
    llm.get_llm.cache_clear()
    db.init()
    journey.reset()


EXPECTED = {
    "ravi": {"reasons": {"THIN_FILE"}, "offers": ["fd_card"]},
    "priya": {"reasons": {"HIGH_FOIR", "HIGH_UTILISATION"}, "offers": ["small_loan"]},
    "sameer": {"reasons": {"RECENT_DPD", "ENQUIRY_SPIKE"}, "offers": ["fd_card"]},
}


@pytest.mark.parametrize("uid", list(EXPECTED))
def test_rejected_then_approved_in_90_days(uid):
    s = journey.apply(uid, None, None, "en")
    assert s["status"] == "rejected"
    assert {r["code"] for r in s["reasons"]} == EXPECTED[uid]["reasons"]
    assert [o["id"] for o in s["offers"]] == EXPECTED[uid]["offers"]
    assert s["plan"]

    readiness = [journey.view(s, "en")["plan"]["readiness"]]
    for day in (30, 60):
        s = journey.advance(uid)
        assert s["day"] == day and s["status"] == "rejected", f"{uid} should not be eligible at day {day}"
        readiness.append(journey.view(s, "en")["plan"]["readiness"])
    s = journey.advance(uid)
    assert s["status"] == "eligible"
    v = journey.view(s, "en")
    assert v["plan"]["readiness"] == 100 and all(r["resolved"] for r in v["reasons"])
    assert readiness == sorted(readiness), "readiness never goes backwards"

    with pytest.raises(PermissionError):
        journey.reapply(uid, consent=False)
    assert journey.reapply(uid, consent=True)["status"] == "approved"
    assert [c["scope"] for c in db.get_consents(uid)] == ["re-apply"]


def test_cannot_reapply_before_eligible():
    journey.apply("ravi", None, None, "en")
    with pytest.raises(ValueError):
        journey.reapply("ravi", consent=True)


def test_plan_amounts_come_from_the_data():
    v = journey.view(journey.apply("priya", None, None, "en"), "en")
    titles = " ".join(a["title"] + " " + a["detail"] for a in v["plan"]["actions"])
    assert "82%" in titles and "30%" in titles
    assert inr(26000) in titles          # 41,000 balance - 30% of 50,000 limit
    assert inr(8000) in titles           # BNPL outstanding


def test_changing_the_amount_changes_the_reasons():
    # At ₹50,000 the EMI load passes, so only card use still blocks.
    s = journey.apply("priya", 50000, 24, "en")
    assert {r["code"] for r in s["reasons"]} == {"HIGH_UTILISATION"}


@pytest.mark.parametrize("lang", ["en", "hi", "mr"])
def test_every_language_renders(lang):
    v = journey.view(journey.apply("sameer", None, None, lang), lang)
    assert v["explanation"]["source"] == "template" and "{" not in v["explanation"]["text"]
    for a in v["plan"]["actions"]:
        assert "{" not in a["title"] + a["detail"]


def test_guard_rejects_invented_numbers():
    facts = {"loan_amount": "₹1,00,000", "util": "82%"}
    assert llm.numbers_ok("Your ₹1,00,000 loan: card use is 82%.", facts)[0]
    assert llm.numbers_ok("आपका कार्ड ८२% भरा है", facts)[0]
    ok, bad = llm.numbers_ok("You will get ₹2,50,000 at 11.5% interest.", facts)
    assert not ok and set(bad) == {"250000", "11.5"}


def test_inr_grouping():
    assert inr(100000) == "₹1,00,000" and inr(1150) == "₹1,150" and inr(12345678) == "₹1,23,45,678"

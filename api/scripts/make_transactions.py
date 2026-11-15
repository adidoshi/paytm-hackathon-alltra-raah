"""Generate the mocked Account Aggregator bank statements and Paytm app records.

Run from the repo root:  api/.venv/Scripts/python -m api.scripts.make_transactions

Writes api/data/transactions/<user>.json. Each row carries a true label ("truth") that is
used only by the tests to score the reader; the API strips it before anything reads the rows.
Day 0 is the day of the rejection (2026-11-15); negative days are the 6 months before it,
days 1-90 are revealed one month at a time by the demo clock.
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

DAY0 = date(2026, 11, 15)
START = -182
END = 90
OUT = Path(__file__).resolve().parents[1] / "data" / "transactions"


class Book:
    def __init__(self, seed: int):
        self.rows: list[dict] = []
        self.rnd = random.Random(seed)

    def ref(self) -> str:
        return str(self.rnd.randint(400000000000, 699999999999))

    def add(self, day: int, amount: float, dir: str, narration: str, source: str, truth: str, due_day: int | None = None):
        if not (START <= day <= END):
            return
        row = {
            "day": day,
            "date": (DAY0 + timedelta(days=day)).isoformat(),
            "amount": int(round(amount)),
            "dir": dir,
            "narration": narration,
            "source": source,
            "truth": truth,
        }
        if due_day is not None:
            row["due_date"] = (DAY0 + timedelta(days=due_day)).isoformat()
        self.rows.append(row)

    def vary(self, base: float, spread: float = 0.12) -> int:
        return int(round(base * (1 + self.rnd.uniform(-spread, spread)) / 10) * 10)

    def done(self, prefix: str) -> list[dict]:
        self.rows.sort(key=lambda r: (r["day"], r["narration"]))
        for i, r in enumerate(self.rows):
            r["id"] = f"{prefix}{i + 1:03d}"
        return self.rows


def month_days(dom: int):
    """Every day offset in range that falls on day-of-month `dom`."""
    d = DAY0 + timedelta(days=START)
    end = DAY0 + timedelta(days=END)
    while d <= end:
        if d.day == dom:
            yield (d - DAY0).days
        d += timedelta(days=1)


def weekdays(weekday: int, every: int = 1):
    """Every `every`-th occurrence of a weekday (0 = Monday) in range."""
    out = []
    d = DAY0 + timedelta(days=START)
    end = DAY0 + timedelta(days=END)
    while d <= end:
        if d.weekday() == weekday:
            out.append((d - DAY0).days)
        d += timedelta(days=1)
    return out[::every]


def mon(day: int) -> str:
    return (DAY0 + timedelta(days=day)).strftime("%b").upper()


# --------------------------------------------------------------------------- Ravi
def ravi() -> list[dict]:
    b = Book(11)
    SBI, PTM = "SBI savings ••4821", "Paytm app"
    for i, d in enumerate(weekdays(0)):  # Swiggy (legal name Bundl Technologies) weekly payout
        if i % 2:
            b.add(d, b.vary(3300), "in", f"NEFT CR-ICIC0000104-BUNDL TECHNOLOGIES PVT LTD-PTR PAYOUT WK{i % 52 + 1}", SBI, "income_gig")
        else:
            b.add(d, b.vary(3300), "in", f"IMPS/P2A/{b.ref()}/BUNDL TECH/ICIC/de payout", SBI, "income_gig")
    for d in weekdays(3, 2):  # Zomato fortnightly settlement
        b.add(d, b.vary(3500), "in", f"UPI/CR/{b.ref()}/ZOMATO LIMITED/YESB/zomato.payout@ybl/Delivery partner settlement", SBI, "income_gig")
    for d in weekdays(5):  # Rapido (legal name Roppen Transportation) weekly
        b.add(d, b.vary(1500, 0.3), "in", f"UPI/CR/{b.ref()}/ROPPEN TRANSPORTATION/UTIB/rapido@axl/captain wkly", SBI, "income_gig")
    for d in month_days(3):
        b.add(d, 7000, "out", f"UPI/DR/{b.ref()}/VITTHAL GAIKWAD/MAHB/vitthalg@okaxis/kholi bhade {mon(d)}", SBI, "rent")
    for d in month_days(5):
        b.add(d, 3000, "out", f"UPI/DR/{b.ref()}/SUNITA JADHAV/BKID/sunitaj@oksbi/aai la", SBI, "transfer_family")
    for d in month_days(12):
        b.add(d, 2000, "out", f"ATM WDL/SBI HINJEWADI PH1/{b.ref()[:6]}", SBI, "cash_withdrawal")
    for d in weekdays(2, 2):
        b.add(d, b.vary(750, 0.2), "out", f"UPI/DR/{b.ref()}/HPCL WAKAD COCO/HDFC/hpcl.wakad@hdfcbank/NA", SBI, "fuel")
    for d in weekdays(6, 2):
        b.add(d, b.vary(800, 0.25), "out", f"UPI/DR/{b.ref()}/SHREE SAMARTH KIRANA/SBIN/9850xxxx12@ybl/NA", SBI, "groceries")
    for d in month_days(21):
        b.add(d, b.vary(320, 0.3), "out", f"UPI/DR/{b.ref()}/Swiggy/ICIC/swiggy.stores@icici/Order", SBI, "food_delivery")
    # Electricity via Paytm: due on the 10th; paid late twice before the rejection, then on AutoPay
    late = {-120: 16, -60: 19}
    for d in month_days(10):
        k = min(late, key=lambda x: abs(x - d))
        paid = d + (late[k] - 10 if abs(k - d) < 15 else -2)
        auto = d > 0
        text = "Paytm AutoPay: Electricity MSEDCL CA 170019XXXX" if auto else "Electricity bill paid - MSEDCL - CA 170019XXXX"
        b.add(paid, b.vary(1150, 0.1), "out", text, PTM, "utility_bill", due_day=d)
    for d in range(START + 4, END, 28):
        b.add(d, 299, "out", "Recharge of Jio Prepaid Mobile 98XXXXXX21", PTM, "mobile_bill", due_day=d)
    # After the rejection: FD-backed card, paid in full each month
    b.add(2, 10000, "out", f"UPI/DR/{b.ref()}/SBM BANK INDIA/SBMI/stepup.fd@sbmbank/FD booking", SBI, "savings")
    for d, amt in [(25, 1900), (55, 2300), (85, 2100)]:
        b.add(d, amt, "out", "ACH D- SBM BANK INDIA-STEPUPCRD-XX1190", SBI, "card_payment")
    return b.done("R")


# --------------------------------------------------------------------------- Priya
def priya() -> list[dict]:
    b = Book(22)
    HD, KO, PTM = "HDFC salary ••0917", "Kotak savings ••4410", "Paytm app"
    for d in month_days(1):
        b.add(d, 45000, "in", f"NEFT CR-CITI0000002-CITIUSTECH LIMITED-SAL {mon(d)}26-PRIYA KULKARNI", HD, "income_salary")
    for d in month_days(2):  # moves money to her second account
        b.add(d, 12000, "out", f"IMPS/P2A/{b.ref()}/PRIYA KULKARNI/KKBK/self", HD, "self_transfer")
        b.add(d, 12000, "in", f"IMPS/{b.ref()}/PRIYA S KULKARNI/HDFC0000917/from hdfc", KO, "self_transfer")
    for d in month_days(3):
        b.add(d, 9000, "out", f"UPI/DR/{b.ref()}/SANJAY KADAM/SBIN/sanjaykadam@okicici/flat 302 {mon(d)}", KO, "rent")
    for d in month_days(5):
        b.add(d, 6500, "out", "ACH D- BAJAJ FINANCE LTD-P400TW8812", HD, "emi")
        b.add(d, 4500, "out", "ACH D- HDB FINANCIAL SERV-PL55190", HD, "emi")
    for d in month_days(7):
        if d <= 75:  # LazyPay EMI, foreclosed in the third month after the rejection
            b.add(d, 3500, "out", f"UPI/DR/{b.ref()}/LAZYPAY/ICIC/lazypay.emi@icici/EMI", HD, "bnpl")
    b.add(78, 4500, "out", f"UPI/DR/{b.ref()}/LAZYPAY/ICIC/lazypay.emi@icici/foreclosure", HD, "bnpl")
    # Not on her bureau report: a weekly hand loan and Simpl
    for d in weekdays(5):
        if d <= 45:
            b.add(d, 700, "out", f"UPI/DR/{b.ref()}/LAXMI ENTERPRISES/BARB/9370xxxx45@ybl/hapta", KO, "informal_loan")
    b.add(52, 2100, "out", f"UPI/DR/{b.ref()}/LAXMI ENTERPRISES/BARB/9370xxxx45@ybl/hapta purna", KO, "informal_loan")
    for d in month_days(15):
        if d <= 30:
            b.add(d, b.vary(1200, 0.15), "out", f"UPI/DR/{b.ref()}/SIMPL TECHNOLOGIES/YESB/simpl@yesbank/bill", KO, "bnpl")
    b.add(40, 2400, "out", f"UPI/DR/{b.ref()}/SIMPL TECHNOLOGIES/YESB/simpl@yesbank/settle all", KO, "bnpl")
    for d in month_days(20):
        if d <= 0:
            b.add(d, 2050, "out", "HDFC BANK CC AUTOPAY 4XXX MIN AMT DUE", HD, "card_payment")
    for d, amt in [(20, 12000), (50, 8000), (80, 6000)]:
        b.add(d, amt, "out", f"BIL/ONL/{b.ref()[:9]}/HDFC CC 4XXX/PAYMENT", HD, "card_payment")
    for i, d in enumerate(weekdays(4)):  # food delivery, cut back after the plan starts
        if d <= 0 or i % 2 == 0:
            b.add(d, b.vary(1150, 0.25), "out", f"UPI/DR/{b.ref()}/ZOMATO/HDFC/zomato-order@ptybl/Payment from Ph", HD, "food_delivery")
    for d in month_days(9):
        b.add(d, b.vary(2000, 0.4), "out", f"UPI/DR/{b.ref()}/MYNTRA DESIGNS/ICIC/myntra@icici/NA", KO, "shopping")
    for d in weekdays(6, 2):
        b.add(d, b.vary(1400, 0.2), "out", f"UPI/DR/{b.ref()}/BLINK COMMERCE PVT LTD/YESB/blinkit@yesbank/NA", KO, "groceries")
    for d in month_days(11):
        b.add(d - 2, b.vary(980, 0.1), "out", "Electricity bill paid - MSEDCL - CA 170044XXXX", PTM, "utility_bill", due_day=d)
    for d in month_days(18):
        b.add(d - 1, 599, "out", "Airtel Postpaid bill payment 99XXXXXX07", PTM, "mobile_bill", due_day=d)
    return b.done("P")


# --------------------------------------------------------------------------- Sameer
def sameer() -> list[dict]:
    b = Book(33)
    SBI, PTM = "SBI savings ••7730", "Paytm app"
    for d in month_days(7):
        late = 3 if -40 < d < -30 else b.rnd.choice([0, 0, 1, -1])  # salary came late in October
        b.add(d + late, 32000, "in", f"UPI/CR/{b.ref()}/SHAIKH TRADERS/BARB/shaikhtraders@okbizaxis/pagaar", SBI, "income_salary")
    for d in month_days(2):
        if -45 < d < -40:  # October EMI bounced: balance was short before salary
            b.add(d, 590, "out", "ACH RTN CHGS INCL GST-TVS CREDIT", SBI, "bank_charges")
            b.add(d + 35, 4200, "out", f"UPI/DR/{b.ref()}/TVS CREDIT SERVICES/HDFC/tvscs.collect@hdfcbank/overdue", SBI, "emi")
        elif d <= 0:
            b.add(d, 4200, "out", "ACH D- TVS CREDIT SERVICES-TW10293", SBI, "emi")
    for d in month_days(10):
        if d > 0:  # EMI date moved after salary, on AutoPay
            b.add(d, 4200, "out", "ACH D- TVS CREDIT SERVICES-TW10293", SBI, "emi")
    # Loan app taken during the application spree, repaid in month one
    b.add(-18, 5000, "in", f"UPI/CR/{b.ref()}/KREDITBEE/RATN/kreditbee.disb@rbl/NA", SBI, "loan_disbursal")
    b.add(12, 5600, "out", f"UPI/DR/{b.ref()}/FINNOVATION TECH/RATN/kreditbee@rbl/repay", SBI, "emi")
    for d in month_days(10):
        b.add(d, 5000, "out", f"UPI/DR/{b.ref()}/AMMI/SBIN/9890xxxx77@ybl/ghar kharch", SBI, "transfer_family")
    for d in weekdays(6, 2):
        b.add(d, b.vary(900, 0.2), "out", f"UPI/DR/{b.ref()}/AL FALAH GENERAL STORE/SBIN/q81236@ybl/NA", SBI, "groceries")
    for d in month_days(15):
        b.add(d, 3000, "out", f"ATM WDL/SBI PIMPRI CAMP/{b.ref()[:6]}", SBI, "cash_withdrawal")
    for d in month_days(25):
        b.add(d, b.vary(600, 0.4), "out", f"UPI/DR/{b.ref()}/AMAZON PAY/YESB/amazon@apl/NA", SBI, "shopping")
    for d in month_days(12):
        b.add(d - 3, b.vary(1400, 0.1), "out", "Electricity bill paid - MSEDCL - CA 170087XXXX", PTM, "utility_bill", due_day=d)
    for d in range(START + 9, END, 28):
        b.add(d, 349, "out", "Recharge of Airtel Prepaid Mobile 97XXXXXX40", PTM, "mobile_bill", due_day=d)
    return b.done("S")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in [("ravi", ravi), ("priya", priya), ("sameer", sameer)]:
        rows = fn()
        (OUT / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        pre = sum(r["day"] <= 0 for r in rows)
        print(f"{name}: {len(rows)} rows ({pre} before the rejection), sources: {sorted({r['source'] for r in rows})}")


if __name__ == "__main__":
    main()

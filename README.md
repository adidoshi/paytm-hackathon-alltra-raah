# Raah

**No loan rejection is a dead end.** Raah is an AI agent that turns a rejected loan application into an approval today or an approval later. It explains the rejection in the customer's language, **reads their bank statements to find the proof the credit bureau couldn't see**, offers what they qualify for now, builds a 90-day plan paid for from their own money, watches their progress, and re-applies with one consent tap.

> The bureau saw no history. The bank statements show 6 months of steady income. Raah's AI reads them and turns them into evidence; the lender's rules decide.

Team Alltra · Paytm Build for India AI Hackathon, Pune · Track 2: AI-Powered Financial Journeys

## Run it

Two terminals, both from the repo root. Needs Python 3.12 and Node 20+.

```bash
# 1. API (http://localhost:8000)
cd api && uv venv --python 3.12 .venv && uv pip install --python .venv -r requirements.txt && cd ..
api/.venv/Scripts/python -m uvicorn api.main:app --reload --port 8000     # macOS/Linux: api/.venv/bin/python

# 2. Web (http://localhost:3000)
cd web && npm install && npm run dev
```

The app works with no keys at all: explanations come from fixed templates and the browser's own voice reads them. To turn on the LLMs and Sarvam voice, copy `.env.example` to `.env` and fill in:

| Key | Turns on |
|---|---|
| `SARVAM_API_KEY` | Sarvam-105B (explanation wording and the "Ask Raah" tool-calling agent), Bulbul v4 text-to-speech, Saaras v4 speech-to-text, and the Sarvam MCP tools |
| `GEMINI_API_KEY` | Gemini as the fallback model if Sarvam-105B fails |

Tests: `api/.venv/Scripts/python -m pytest api/tests -q`

**Before a demo**, pre-generate every explanation and its audio, so the live run is served from disk with no credits used and no network needed:

```bash
api/.venv/Scripts/python -m api.scripts.pregen
```

### Where Sarvam AI is used

| Step | Sarvam | Model |
|---|---|---|
| **Read bank statements**: label every raw transaction | Chat completion returning labels only, never amounts | `sarvam-105b-conversations` |
| Explain the rejection in Marathi, Hindi or English | Chat completion, number-checked against the rules | `sarvam-105b-conversations` |
| Read the explanation and answers aloud | Text-to-speech, one voice per language | `bulbul:v4-flash` (`nilesh_mr_conversation`, `shubh_enhi_banking`) |
| Customer asks by voice | Speech-to-text with automatic language detection | `saaras:v4` |
| "Ask Raah" agent | Tool calling inside the LangGraph agent (about 1 s per answer) | `sarvam-105b-conversations` |
| Agent tools | Sarvam MCP server (`uvx sarvam-mcp`): `translate`, `identify_language` | MCP over stdio |

Fallback order everywhere: Sarvam → Gemini → fixed template. The Agent trace panel shows which one answered.

## Why an LLM: the statement reader

A credit bureau only sees past loans and cards. A customer's bank statements show what the lender can't see: real income, real obligations, bill discipline, spending. But statement narrations are raw text that keyword rules cannot read:

| Narration | Keyword rules say | Raah's reader says |
|---|---|---|
| `UPI/CR/…/ROPPEN TRANSPORTATION/…/captain wkly` | other | gig income (Roppen = Rapido) |
| `UPI/CR/…/SHAIKH TRADERS/…/pagaar` | other | salary ("pagaar") |
| `IMPS/…/PRIYA S KULKARNI/HDFC0000917/from hdfc` | other | her own account, not income |
| `ACH D- SBM BANK INDIA-STEPUPCRD-XX1190` | EMI | credit card bill |
| `UPI/DR/…/LAXMI ENTERPRISES/…/hapta` | other | hand loan, not on the bureau report |
| `UPI/DR/…/VITTHAL GAIKWAD/…/kholi bhade NOV` | other | rent ("kholi bhade") |
| `UPI/CR/…/KREDITBEE/…` | other | borrowed money, not income |
| `UPI/DR/…/LAXMI ENTERPRISES/…/hapta purna` | other | hand loan, final payment |

Measured on the demo statements (each row hand-labelled; the labels never reach the model):

| Customer | Reader (Sarvam-105B) | Keyword rules | Monthly income found: reader vs keywords |
|---|---|---|---|
| Ravi, delivery partner | 99% | 71% | ₹28,295 vs ₹20,900 |
| Priya, salaried | 97% | 62% | ₹45,000 vs ₹45,000, plus 2 debts missing from her bureau report |
| Sameer, shop employee | 100% | 76% | ₹32,000 vs **₹0** |

What the evidence changes:
- **Ravi** gets a ₹40,000 cash-flow loan **today**, approved on his statements.
- **Priya**'s hidden debts (a weekly hand loan and Simpl) are counted: her offer drops honestly from ₹75,000 to ₹50,000, and her plan clears them first. Her card payoff is paid for from her own money: spare cash, dues cleared, less food delivery and shopping.
- **Sameer**'s missed EMI turns out to be a timing problem: salary lands on day 7, the EMI is taken on day 2. The first plan step moves the EMI date.

**What if they pay with another UPI app?** UPI apps hold no money; every payment from PhonePe, GPay or Paytm is a debit on a bank account. Raah reads bank statements through RBI's **Account Aggregator** framework with one consent, covering every linked account. Paytm's own records (bills, AutoPay mandates) add detail where available. If something is missing (no rent seen), Raah asks one question and records the answer as self-declared.

## How it works

```
Loan rejected ──> LangGraph pipeline
                  fetch_data → decode_reasons → match_offers → build_plan → compose_explanation → validate
                                 (rules)          (rules)        (rules)        (LLM + number guard)

Consent (Account Aggregator) ──> reader labels every transaction (LLM, labels only)
                             ──> cash-flow profile: income, hidden debts, bills, salary/EMI days (rules)
                             ──> reasons, offers and plan re-run on the evidence (rules)

New month of statements ──> reader labels only the new rows ──> watcher re-runs the rules ──> nudge
All rules pass ──> consent sheet ──> lender re-apply ──> approved
```

- **Rules decide.** `api/rules/thresholds.yaml` and `products.yaml` hold every number. `api/rules/engine.py` and `api/rules/cashflow.py` are pure Python with no LLM.
- **The reader only labels.** `api/agent/reader.py` returns a label from a fixed list and a counterparty name per transaction id. Unknown ids, unknown labels and any other fields are dropped. Every total is computed from the raw amounts in `cashflow.py`.
- **The LLM explains.** Sarvam-105B receives rule output as JSON and phrases it. `numbers_ok` in `api/agent/llm.py` rejects any reply containing a figure the rules did not produce, and the fixed template is used instead.
- **The user consents.** The agent's `request_reapply` tool cannot submit anything. Only the consent sheet calls `/api/reapply`, and every consent is written to `consent_log`.
- **Everything is audited.** Each rule, tool call, LLM call, guard result and consent is logged and shown live in the Agent trace panel.

| Path | What is in it |
|---|---|
| `api/rules/` | Rules engine, cash-flow profile, thresholds, product catalogue, English / Hindi / Marathi wording |
| `api/agent/` | Statement reader, LangGraph rejection pipeline, chat agent and tools, LLM guard |
| `api/services/` | Journey state machine, statement reading and funding, Sarvam client with audio cache, lender / bureau / Account Aggregator / Paytm adapters |
| `api/mock/`, `api/data/` | Mocked outside systems, the three seeded customers, their bank statements, and saved model answers (`llm_cache`, `audio`) |
| `web/components/` | `Phone` and `ProofStep` (customer journey), `Stage` (rules view, statement reader, demo clock), `TracePanel` (audit trail) |

## What is real and what is mocked

Real: the statement reader, rules engine, agent pipeline, guardrails, consent and audit log, voice, the full UI.
Mocked behind adapters in `api/services/clients.py`: the lender decision, the bureau report, the Account Aggregator bank statements (generated by `api/scripts/make_transactions.py`), and Paytm bill records. The "Simulate +30 days" button plays the next month of that data so a 90-day plan can be shown in a minute.

## Demo script (3 minutes)

1. Ravi, a delivery partner, applies for ₹1,00,000. The lender says no with a one-line sorry: today's dead end.
2. Raah appears: "This is not the end." It explains in Marathi, by voice, that he has no credit history.
3. **Proof**: "Your credit report isn't the whole story." One Account Aggregator consent. The reader goes through 129 transactions: ₹28,295 a month from Swiggy, Zomato and Rapido payouts, which keyword rules would mostly miss. Point at the stage: reader 99% right, keyword rules 71%.
4. **Today**: a ₹40,000 cash-flow loan, approved on his statements, plus an FD-backed card to build his credit record.
5. **Plan**: tap **Simulate +30 days** three times; the reader labels each new month, the ring fills, nudges arrive.
6. Day 90: "You now qualify." Consent sheet → re-apply → **Approved** for the full ₹1,00,000.
7. Point at the trace: the AI read the evidence; the rules made every decision; the customer consented twice.

Switch to Priya (hidden debts found, honest smaller offer, plan paid for from her own spending) or Sameer (₹0 income for keyword rules, salary-vs-EMI timing) to show the engine is general. "Reset demo" starts clean.

### Mentor questions, answered

- **Why does this need an LLM, and is it worth the cost?** Reading raw Indian bank narrations: legal names instead of brands, Hindi and Marathi notes, P2P transfers, loan apps. Keyword rules get 62–76% right and miss income entirely for Sameer; the reader gets 97–100%. Each statement is read once and new months incrementally, so it is about one model call per 30 transactions. Today lenders pay analysts or statement-analysis vendors for this.
- **What does bureau data add, and what do the transactions add?** The bureau is the past credit record, and the lender's reason for the no. The statements are real income, real obligations (including debts the bureau never sees), bill discipline and spending. One explains the no; the other is how it becomes a yes.
- **What if the customer pays with other UPI apps?** It doesn't matter: Raah reads bank statements via Account Aggregator, and every UPI app debits a bank account.
- **Does the AI decide credit?** No. It returns labels only. Every amount is summed in code, and every decision is a rule in a YAML file the lender owns.

## Deploy

- **API on Render:** root directory = repo root, build `pip install -r api/requirements.txt`, start `uvicorn api.main:app --host 0.0.0.0 --port $PORT`, Python 3.12. Add the keys from `.env.example`. SQLite is rebuilt from the persona files on every start, so the free tier's wiped disk is not a problem.
- **Web on Vercel:** root directory = `web`, env `NEXT_PUBLIC_API_URL` = the Render URL.
- Free Render sleeps when idle; open the URL a few minutes before showing it. Demo from localhost when you can.

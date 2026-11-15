# Raah

**No loan rejection is a dead end.** Raah is an AI agent that turns a rejected loan application into an approval today or an approval later: it explains the rejection in the customer's language, offers what they qualify for now, builds a 90-day plan from their own Paytm data, watches their progress, and re-applies with one consent tap.

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
| Explain the rejection in Marathi, Hindi or English | Chat completion, number-checked against the rules | `sarvam-105b-conversations` |
| Read the explanation and answers aloud | Text-to-speech, one voice per language | `bulbul:v4-flash` (`nilesh_mr_conversation`, `shubh_enhi_banking`) |
| Customer asks by voice | Speech-to-text with automatic language detection | `saaras:v4` |
| "Ask Raah" agent | Tool calling inside the LangGraph agent (about 1 s per answer) | `sarvam-105b-conversations` |
| Agent tools | Sarvam MCP server (`uvx sarvam-mcp`): `translate`, `identify_language` | MCP over stdio |

Fallback order everywhere: Sarvam → Gemini → fixed template. The Agent trace panel shows which one answered.

## How it works

```
Loan rejected ──> LangGraph pipeline
                  fetch_data → decode_reasons → match_offers → build_plan → compose_explanation → validate
                                 (rules)          (rules)        (rules)        (LLM + number guard)

New Paytm / bureau event ──> eligibility watcher re-runs the same rules ──> nudge
All rules pass ──> consent sheet ──> lender re-apply ──> approved
```

- **Rules decide.** `api/rules/thresholds.yaml` and `products.yaml` hold every number. `api/rules/engine.py` is pure Python with no LLM.
- **The LLM explains.** Sarvam-105B receives rule output as JSON and phrases it. `numbers_ok` in `api/agent/llm.py` rejects any reply containing a figure the rules did not produce, and the fixed template is used instead.
- **The user consents.** The agent's `request_reapply` tool cannot submit anything. Only the consent sheet calls `/api/reapply`, and every consent is written to `consent_log`.
- **Everything is audited.** Each rule, tool call, LLM call, guard result and consent is logged and shown live in the Agent trace panel.

| Path | What is in it |
|---|---|
| `api/rules/` | Rules engine, thresholds, product catalogue, English / Hindi / Marathi wording |
| `api/agent/` | LangGraph rejection pipeline, chat agent and tools, LLM guard |
| `api/services/` | Journey state machine, Sarvam client with audio cache, lender / bureau / Paytm adapters |
| `api/mock/`, `api/data/personas/` | Mocked outside systems and the three seeded customers |
| `web/components/` | `Phone` (customer journey), `Stage` (customer data and demo clock), `TracePanel` (audit trail) |

## What is real and what is mocked

Real: rules engine, agent pipeline, guardrails, consent and audit log, voice, the full UI.
Mocked behind adapters in `api/services/clients.py`: the lender decision, the bureau report, and the customer's Paytm bill, UPI and EMI data. The "Simulate +30 days" button plays the next month of that data so a 90-day plan can be shown in a minute.

## Demo script (3 minutes)

1. Ravi, a delivery partner, applies for ₹1,00,000. The lender says no with a one-line sorry: today's dead end.
2. Raah appears: "This is not the end." It explains in Marathi, by voice, that he has no credit history.
3. Today: an FD-backed card he qualifies for now. Tap "Start with this" (consent logged).
4. Plan: three actions built from his own data. Tap **Simulate +30 days** three times; the ring fills, nudges arrive.
5. Day 90: "You now qualify." Consent sheet → re-apply → **Approved**.
6. Point at the trace: the LLM never decided anything.

Switch to Priya (card nearly full, high EMI load) or Sameer (missed EMI, too many applications) to show the engine is general. "Reset demo" starts clean.

## Deploy

- **API on Render:** root directory = repo root, build `pip install -r api/requirements.txt`, start `uvicorn api.main:app --host 0.0.0.0 --port $PORT`, Python 3.12. Add the keys from `.env.example`. SQLite is rebuilt from the persona files on every start, so the free tier's wiped disk is not a problem.
- **Web on Vercel:** root directory = `web`, env `NEXT_PUBLIC_API_URL` = the Render URL.
- Free Render sleeps when idle; open the URL a few minutes before showing it. Demo from localhost when you can.

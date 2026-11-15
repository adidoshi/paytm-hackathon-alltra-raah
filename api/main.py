"""Raah API. Run from the repo root:  uvicorn api.main:app --reload --port 8000"""
from __future__ import annotations

import asyncio
import base64
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure root and api are on sys.path and set __package__ for Vercel Serverless
_this_dir = Path(__file__).resolve().parent
_repo_root = _this_dir.parent
for _p in [str(_repo_root), str(_this_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

if not __package__:
    __package__ = "api"

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import config, db
from .agent import chat as chat_agent
from .agent import llm
from .mock.routers import router as mock_router
from .rules import engine
from .rules.i18n import T
from .services import journey, sarvam


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    journey.reset()  # every start is a clean demo
    mcp_task = asyncio.create_task(chat_agent.run_mcp())  # starts in the background
    print(f"[raah] Explanation LLM: {', then '.join(llm.model_name(p) for p in llm.providers()) or 'templates only'} | "
          f"Agent LLM: {', then '.join(llm.model_name(p) for p in llm.agent_providers()) or 'off (intent router)'} | "
          f"Sarvam voice: {'on' if sarvam.enabled() else 'off (cached audio only)'}")
    yield
    chat_agent.stop_mcp()
    try:
        await asyncio.wait_for(mcp_task, timeout=5)
    except Exception:
        pass


app = FastAPI(title="Raah API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.middleware("http")
async def ensure_cors_headers(request: Request, call_next):
    origin = request.headers.get("origin") or "*"
    if request.method == "OPTIONS":
        response = JSONResponse(content={"ok": True}, status_code=200)
    else:
        try:
            response = await call_next(request)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            response = JSONResponse(
                status_code=500,
                content={"detail": str(exc)},
            )
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    origin = request.headers.get("origin") or "*"
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*",
        },
    )
app.include_router(mock_router)


def _lang(lang: str | None) -> str:
    return lang if lang in T else "en"


def _view(user_id: str, lang: str) -> dict:
    try:
        return journey.view(journey.state_of(user_id), _lang(lang))
    except KeyError:
        raise HTTPException(404, "unknown user")


class ApplyBody(BaseModel):
    user_id: str
    amount: int | None = None
    tenure_months: int | None = None
    lang: str = "en"


class UserBody(BaseModel):
    user_id: str
    lang: str = "en"


class OfferBody(UserBody):
    offer_id: str


class ReapplyBody(UserBody):
    consent: bool = False


class GapBody(UserBody):
    gap: str
    answer: str


class ChatBody(UserBody):
    message: str
    speak: bool = False


class TtsBody(BaseModel):
    text: str
    lang: str = "en"


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "llm": bool(llm.providers()),
        "voice": sarvam.enabled(),
        "explain_models": [llm.model_name(p) for p in llm.providers()],
        "agent_models": [llm.model_name(p) for p in llm.agent_providers()],
        "tts": f"{config.SARVAM_TTS_MODEL}" if sarvam.enabled() else None,
        "stt": f"{config.SARVAM_STT_MODEL}" if sarvam.enabled() else None,
        "speakers": config.SARVAM_SPEAKERS,
        "mcp": chat_agent.mcp_status(),
    }


@app.get("/api/personas")
def personas():
    return journey.personas()


@app.get("/api/policy")
def policy():
    """The thresholds and product rules, shown in the UI to prove rules decide."""
    return {"thresholds": engine.TH, "products": engine.PRODUCTS}


@app.post("/api/applications")
def apply(body: ApplyBody):
    try:
        s = journey.apply(body.user_id, body.amount, body.tenure_months, _lang(body.lang))
    except KeyError:
        raise HTTPException(404, "unknown user")
    return journey.view(s, _lang(body.lang))


@app.get("/api/journey/{user_id}")
def get_journey(user_id: str, lang: str = "en"):
    return _view(user_id, lang)


@app.post("/api/offers/accept")
def accept_offer(body: OfferBody):
    try:
        s = journey.accept_offer(body.user_id, body.offer_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return journey.view(s, _lang(body.lang))


@app.post("/api/statements/read")
def read_statements(body: UserBody):
    """Consent tap on the phone: fetch bank statements via Account Aggregator and read them."""
    try:
        s = journey.read_statements(body.user_id)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return journey.view(s, _lang(body.lang))


@app.post("/api/statements/answer")
def answer_gap(body: GapBody):
    return journey.view(journey.answer_gap(body.user_id, body.gap, body.answer), _lang(body.lang))


@app.post("/api/simulate/advance")
def advance(body: UserBody):
    return journey.view(journey.advance(body.user_id), _lang(body.lang))


@app.post("/api/reapply")
def reapply(body: ReapplyBody):
    try:
        s = journey.reapply(body.user_id, body.consent)
    except PermissionError:
        raise HTTPException(403, "Consent is required to re-apply")
    except ValueError as e:
        raise HTTPException(409, str(e))
    return journey.view(s, _lang(body.lang))


@app.get("/api/trace/{user_id}")
def trace(user_id: str, after: int = 0):
    return {"entries": db.get_trace(user_id, after), "consents": db.get_consents(user_id)}


@app.post("/api/demo/reset")
def demo_reset():
    journey.reset()
    return {"ok": True}


def _speak(user_id: str, text: str, lang: str) -> dict | None:
    try:
        audio, cached = sarvam.tts(text, lang)
    except sarvam.SarvamError as e:
        if user_id:
            db.trace(user_id, "voice", "Sarvam TTS unavailable", str(e)[:160])
        return None
    if user_id:
        db.trace(user_id, "voice", f"Sarvam TTS ({config.SARVAM_TTS_MODEL}, {sarvam.speaker_for(lang)})", "served from cache" if cached else f"{len(text)} characters")
    return {"audio_b64": base64.b64encode(audio).decode(), "mime": "audio/wav", "cached": cached}


@app.post("/api/tts")
async def tts(body: TtsBody, user_id: str = ""):
    out = await run_in_threadpool(_speak, user_id, body.text, _lang(body.lang))
    if out is None:
        raise HTTPException(503, "Voice is unavailable")
    return out


@app.post("/api/chat")
async def chat(body: ChatBody):
    lang = _lang(body.lang)
    result = await chat_agent.answer(body.user_id, body.message, lang)
    audio = await run_in_threadpool(_speak, body.user_id, result["reply"], lang) if body.speak else None
    return {**result, "lang": lang, "audio": audio}


@app.post("/api/voice/ask")
async def voice_ask(user_id: str = Form(...), lang: str = Form("en"), file: UploadFile = File(...)):
    data = await file.read()
    try:
        heard = await run_in_threadpool(sarvam.stt, data, file.filename or "question.webm", file.content_type or "audio/webm")
    except sarvam.SarvamError as e:
        db.trace(user_id, "voice", "Sarvam STT unavailable", str(e)[:160])
        raise HTTPException(503, "Voice is unavailable")
    reply_lang = heard["lang"] or _lang(lang)
    db.trace(user_id, "voice", f"Sarvam STT ({config.SARVAM_STT_MODEL})", f"heard [{reply_lang}]: {heard['transcript'][:120]}")
    if not heard["transcript"]:
        raise HTTPException(422, "Could not hear anything")
    result = await chat_agent.answer(user_id, heard["transcript"], reply_lang)
    audio = await run_in_threadpool(_speak, user_id, result["reply"], reply_lang)
    return {**result, "transcript": heard["transcript"], "lang": reply_lang, "audio": audio}

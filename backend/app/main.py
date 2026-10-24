"""Amma ji's backend. Keeps the API keys safe and runs the cooking loop.

Run from the backend folder:  .venv/bin/uvicorn app.main:app --reload --port 8010
Then open http://localhost:8010/docs to try every endpoint in the browser.
"""
import itertools
import logging
import os
import threading
import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import brain, finish, pantry, quick, voice
from .session import RECIPES, SESSIONS, apply_tool, go_to_step, new_session, public, remember_turn

app = FastAPI(title="Amma ji")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://localhost:4173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Sample-Rate", "X-First-Audio-Ms"],
)

Language = Literal["hi-en", "hi", "pa", "en"]
MAX_AUDIO_BYTES = 16000 * 2 * 30 + 44  # 30 seconds of 16 kHz mono WAV
# Our own lines (like "how was it?" answers) go to the server log next to uvicorn's
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


class NewSession(BaseModel):
    recipe_id: str = "dal_tadka"
    language: Language = "hi-en"
    teasing: bool = True
    allergies: list[str] = []


class Say(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class Step(BaseModel):
    action: Literal["next", "previous"]


class Timer(BaseModel):
    minutes: float = Field(gt=0, le=180)
    label: str = Field(default="timer", max_length=40)


class Pantry(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    language: Language = "hi-en"


class Suggest(BaseModel):
    have: list[str] = []
    not_have: list[str] = []
    minutes: int | None = Field(default=None, gt=0, le=600)
    diet: Literal["veg"] | None = None
    allergies: list[str] = []
    kinds: list[str] | None = None
    language: Language = "hi-en"
    limit: int = Field(default=3, ge=1, le=10)


class Pick(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    options: list[str] = Field(min_length=1, max_length=10)


class Feedback(BaseModel):
    rating: Literal["loved", "okay", "bad"]


class Speak(BaseModel):
    text: str = Field(min_length=1, max_length=600)
    language: Language = "hi-en"
    speed: float = Field(default=1.0, ge=0.85, le=1.15)


def get_session(session_id):
    state = SESSIONS.get(session_id)
    if not state:
        raise HTTPException(404, "This cooking session has ended. Start a new one.")
    return state


def run_turn(state, text):
    """One turn, whether it was typed or spoken: Groq picks a tool, code carries it out.
    Plain commands like "agla step" are answered in code and never reach Groq."""
    start = time.perf_counter()
    intent = quick.match(text)
    if intent:
        tool, args, effect, said, spoken = quick.answer(state, intent)
        remember_turn(state, text, said)
        return {
            "heard": text, "tool": tool, "args": args,
            "reply": spoken,  # her short answer, then the step, for Timbre
            "reply_text": said,  # only the short answer on screen: the step is already shown big
            "effect": effect, "warnings": [], "state": public(state), "answered_by": "code",
            "timing_ms": {"groq": 0, "total": round((time.perf_counter() - start) * 1000)},
            "tokens": {"total": 0, "prompt": 0},
        }
    try:
        turn = brain.ask(state, text)
    except brain.BrainError as e:
        raise HTTPException(503, str(e))
    effect = apply_tool(state, turn["tool"], turn["args"])
    if turn["tool"] == "check_timer":
        turn["reply"] = brain.timer_reply(state)  # timers are code's job, so code answers
    remember_turn(state, text, turn["reply"])
    return {
        "heard": text,
        "tool": turn["tool"],
        "args": turn["args"],
        "reply": turn["reply"],  # with audio tags, for Timbre
        "reply_text": brain.screen_text(turn["reply"]),  # without tags, for the screen
        "effect": effect,
        "warnings": brain.warnings(turn["reply"]),
        "state": public(state),
        "timing_ms": {"groq": turn["ms"], "total": round((time.perf_counter() - start) * 1000)},
        "tokens": {"total": turn["tokens"], "prompt": turn["prompt_tokens"]},
        "answered_by": "groq",
    }


@app.get("/api/health")
def health():
    return {"ok": True, "recipes": len(RECIPES), "groq_key": bool(os.getenv("GROQ_API_KEY")),
            "gnani_key": bool(os.getenv("GNANI_API_KEY"))}


@app.get("/api/recipes")
def recipes(language: Language = "hi-en"):
    """Every dish that can be cooked with Amma ji (it has steps)."""
    out = []
    for r in RECIPES.values():
        c = pantry.card(r, language)
        out.append({k: c[k] for k in ("id", "name", "kind", "diet", "minutes")})
    return sorted(out, key=lambda x: x["name"])


@app.get("/api/recipes/{recipe_id}")
def recipe(recipe_id: str, language: Language = "hi-en"):
    """Flow D: the recipe card."""
    if recipe_id not in RECIPES:
        raise HTTPException(404, "Amma ji does not know that dish yet.")
    return pantry.card(RECIPES[recipe_id], language)


@app.get("/api/ingredients")
def ingredients(language: Language = "hi-en"):
    return pantry.ingredient_list(language)


@app.post("/api/hear")
async def hear(request: Request, language: Language = "hi-en"):
    """Speech to text only, for telling Amma ji what is in the kitchen. The body is a WAV. Nothing is saved."""
    audio = await request.body()
    if len(audio) < 16000 or len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(422, "That recording was too short or too long. Hold the mic and try again.")
    try:
        text, ms = voice.stt(audio, language)
    except voice.VoiceError as e:
        raise HTTPException(502, str(e))
    if not text:
        raise HTTPException(422, "Amma ji did not catch that. Come a little closer and try again.")
    return {"text": text, "stt_ms": ms}


@app.post("/api/pantry")
def understand_pantry(body: Pantry):
    """Flow B: what the cook has, from what they said or typed. Plain code, no AI."""
    heard = pantry.hear(body.text)
    # "say" is the name in the script Timbre reads well: आलू even on a Hinglish screen that shows aloo
    named = lambda ids: [{"id": i, "name": pantry.display_name(i, body.language),
                          "say": pantry.ingredient_name(i, body.language)} for i in ids]
    return {**heard, "have": named(heard["have"]), "not_have": named(heard["not_have"])}


@app.post("/api/suggest")
def suggest(body: Suggest):
    """Flow C: the best dishes for what the cook has, ranked in code with honest labels."""
    return pantry.suggest(body.have, body.not_have, body.minutes, body.diet, body.allergies, body.kinds,
                          body.language, body.limit)


@app.post("/api/pick")
def pick(body: Pick):
    """Flow C by voice: "doosra wala" or "aloo paratha wala" picks one of the dishes on screen. No AI."""
    return pantry.pick(body.text, body.options)


@app.post("/api/sessions")
def start(body: NewSession):
    try:
        state = new_session(body.recipe_id, body.language, body.teasing, body.allergies)
    except KeyError:
        raise HTTPException(404, f"No recipe called {body.recipe_id}.")
    # Open the STT and Groq connections now, so the first question is answered faster
    threading.Thread(target=lambda: (voice.warm(), brain.warm()), daemon=True).start()
    return public(state)


@app.get("/api/sessions/{session_id}")
def read(session_id: str):
    return public(get_session(session_id))


@app.post("/api/sessions/{session_id}/step")
def step(session_id: str, body: Step):
    """The Back and Next buttons. No AI needed for a tap."""
    state = get_session(session_id)
    go_to_step(state, state["current_step"] + (1 if body.action == "next" else -1))
    return public(state)


@app.post("/api/sessions/{session_id}/timer")
def timer(session_id: str, body: Timer):
    """Start a timer from a tap. No AI needed."""
    state = get_session(session_id)
    apply_tool(state, "start_timer", {"minutes": body.minutes, "label": body.label})
    return public(state)


@app.post("/api/sessions/{session_id}/finish")
def done(session_id: str):
    """Flow F: the dish is ready. The summary and Amma ji's last line are built in code."""
    return finish.summary(get_session(session_id))


@app.post("/api/sessions/{session_id}/feedback")
def how_was_it(session_id: str, body: Feedback):
    return finish.feedback(get_session(session_id), body.rating)


@app.post("/api/sessions/{session_id}/say")
def say(session_id: str, body: Say):
    """One typed turn."""
    return run_turn(get_session(session_id), body.text)


@app.post("/api/sessions/{session_id}/listen")
async def listen(session_id: str, request: Request):
    """One spoken turn. The body is a WAV recording (mono, 16 kHz). Nothing is saved."""
    state = get_session(session_id)
    audio = await request.body()
    if len(audio) < 16000 or len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(422, "That recording was too short or too long. Hold the mic and try again.")
    try:
        heard, stt_ms = voice.stt(audio, state["language"])
    except voice.VoiceError as e:
        raise HTTPException(502, str(e))
    if not heard:
        raise HTTPException(422, "Amma ji did not catch that. Come a little closer and try again.")
    result = run_turn(state, heard)
    result["timing_ms"]["stt"] = stt_ms
    return result


@app.post("/api/speak")
def speak(body: Speak):
    """Amma ji's voice, streamed: raw 16-bit PCM at 24 kHz, sent piece by piece as Timbre makes it."""
    start = time.perf_counter()
    pieces = voice.tts_chunks(body.text, body.language, body.speed)
    try:
        first = next(pieces)  # wait for the first piece, so a failure can still return a clear error
    except (voice.VoiceError, StopIteration) as e:
        raise HTTPException(502, str(e) or "Amma ji lost her voice. Try again.")
    first_ms = round((time.perf_counter() - start) * 1000)
    return StreamingResponse(
        itertools.chain([first], pieces),
        media_type="application/octet-stream",
        headers={"X-Sample-Rate": str(voice.SAMPLE_RATE), "X-First-Audio-Ms": str(first_ms)},
    )


# On the web, this server also hands out the built app (frontend/dist), so the app and its API
# share one address: no cross-site setup, and the browser allows the mic over that one HTTPS link.
# Mounted last, so every /api route above still wins.
APP = Path(os.getenv("APP_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
if APP.is_dir():
    app.mount("/", StaticFiles(directory=APP, html=True), name="app")

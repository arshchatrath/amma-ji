"""Amma ji's backend. Keeps the API keys safe and runs the cooking loop.

Run from the backend folder:  .venv/bin/uvicorn app.main:app --reload
Then open http://localhost:8000/docs to try every endpoint in the browser.
"""
import os
import time
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import brain
from .session import RECIPES, SESSIONS, apply_tool, go_to_step, new_session, public, remember_turn

app = FastAPI(title="Amma ji")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://localhost:4173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class NewSession(BaseModel):
    recipe_id: str = "dal_tadka"
    language: Literal["hi-en", "hi", "pa", "en"] = "hi-en"
    teasing: bool = True
    allergies: list[str] = []


class Say(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class Step(BaseModel):
    action: Literal["next", "previous"]


def get_session(session_id):
    state = SESSIONS.get(session_id)
    if not state:
        raise HTTPException(404, "This cooking session has ended. Start a new one.")
    return state


@app.get("/api/health")
def health():
    return {"ok": True, "recipes": len(RECIPES), "groq_key": bool(os.getenv("GROQ_API_KEY"))}


@app.get("/api/recipes")
def recipes():
    return [{"id": r["id"], "name": r["name"], "servings": r["servings"],
             "minutes": r["prep_min"] + r["cook_min"]} for r in RECIPES.values()]


@app.post("/api/sessions")
def start(body: NewSession):
    try:
        state = new_session(body.recipe_id, body.language, body.teasing, body.allergies)
    except KeyError:
        raise HTTPException(404, f"No recipe called {body.recipe_id}.")
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


@app.post("/api/sessions/{session_id}/say")
def say(session_id: str, body: Say):
    """One spoken (or typed) turn: Groq picks a tool and writes the reply, code carries out the tool."""
    state = get_session(session_id)
    start = time.perf_counter()
    try:
        turn = brain.ask(state, body.text)
    except brain.BrainError as e:
        raise HTTPException(503, str(e))
    effect = apply_tool(state, turn["tool"], turn["args"])
    if turn["tool"] == "check_timer":
        turn["reply"] = brain.timer_reply(state)  # timers are code's job, so code answers
    remember_turn(state, body.text, turn["reply"])
    return {
        "tool": turn["tool"],
        "args": turn["args"],
        "reply": turn["reply"],               # with audio tags, for Timbre
        "reply_text": brain.screen_text(turn["reply"]),  # without tags, for the screen
        "effect": effect,
        "warnings": brain.warnings(turn["reply"]),
        "state": public(state),
        "timing_ms": {"groq": turn["ms"], "total": round((time.perf_counter() - start) * 1000)},
        "tokens": {"total": turn["tokens"], "prompt": turn["prompt_tokens"]},
    }

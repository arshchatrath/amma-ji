# Amma ji backend

Keeps the API keys safe and runs the cooking loop. Python + FastAPI.

## Run it

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload --port 8010
```

Keys come from environment variables, or from `backend/.env` (copy `.env.example`): `GNANI_API_KEY`,
`GROQ_API_KEY`, and optionally `GROQ_MODEL`, `TTS_VOICE` (default Chetana), `FRONTEND_ORIGINS`. Then open
http://localhost:8010/docs to try every endpoint in the browser.

## Endpoints

| Method | Path | What it does |
|---|---|---|
| GET | `/api/health` | Is the server up, is the Groq key set |
| GET | `/api/recipes` | Recipe list |
| POST | `/api/sessions` | Start cooking: `{recipe_id, language, teasing, allergies}` |
| GET | `/api/sessions/{id}` | Current state, live timers, current step |
| POST | `/api/sessions/{id}/step` | Back and Next buttons: `{action: "next" or "previous"}`, no AI |
| POST | `/api/sessions/{id}/timer` | Start a timer from a tap: `{minutes, label}`, no AI |
| POST | `/api/sessions/{id}/say` | One typed turn: `{text}`. Groq picks a tool and writes the reply, code carries it out |
| POST | `/api/sessions/{id}/listen` | One spoken turn: the body is a WAV (mono, 16 kHz). Prisma STT, then the same turn as `/say` |
| POST | `/api/speak` | Amma ji's voice: `{text, language, speed}`. Streams raw 16-bit PCM at 24 kHz as Timbre makes it |

Gnani allows one voice (TTS) request at a time per account, so a new `/speak` cuts off the one
still playing. Two people using the app at the same moment will cut each other off.

## How a turn works

1. `session.normalise()` swaps ingredient words in English letters for their proper name
   (ghee becomes घी), so the reply comes out in one script
2. `brain.note()` writes a short note from the session: steps around the current one, ingredients
   with their Hindi or Punjabi names, safe substitutes (allergies removed), what is already added,
   swaps, timers, the last 3 exchanges
3. `brain.ask()` sends it to Groq (gpt-oss-120b) with 11 tools. One call returns the tool and what
   Amma ji says
4. `session.apply_tool()` does the work in code: moves the step, records ingredients and swaps,
   starts timers. "How much time is left" is answered by code from the clock, not by the AI
5. `brain.warnings()` flags slips worth a look while testing (mixed scripts, male verb forms)

## Tests

```
.venv/bin/pytest
```

`day1/` holds the Day 1 feasibility scripts (voices, STT, Groq comparison, full pipeline timing).

# Amma ji

A voice cooking companion that talks to you in Hinglish, Hindi, Punjabi or English, knows which
step you're on, catches your mistakes and fixes them. Built on Gnani's Prisma STT and Timbre v3.0,
with Groq for the thinking. The full plan is in `AMMA_JI_BRIEF.md`.

## Run it on your computer

Two terminals.

Backend (Python, needs `GNANI_API_KEY` and `GROQ_API_KEY` set):

```
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload --port 8010
```

Frontend (Node):

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, pick a language and tap "Start cooking". Tell Amma ji what you have,
pick a dish, then tap the kadhai and talk. Add `?dev` to the address to see how long each part of a
turn takes.

## Put it on the web

One service serves both the app and its API from one HTTPS address, which phones need before
they allow the mic. The `Dockerfile` builds it; `render.yaml` sets it up on Render's free plan:

1. On render.com: New > Blueprint, and pick this repository.
2. Render reads `render.yaml` and asks for `GNANI_API_KEY` and `GROQ_API_KEY`. Paste them there
   (they stay in Render's settings, never in the repo), then create the service.
3. The first build takes a few minutes. The app opens at the `onrender.com` address Render shows.

On the free plan the service sleeps after 15 minutes without visits, so the first visit after
that takes about a minute. Cooking sessions live in memory, so a restart ends any that are open.

## Amma ji's voice outside cooking

She greets you, asks what is in your kitchen, reacts to what you say, asks about time and allergies,
then reads out her top dishes. Fixed lines are in `frontend/src/data/lines.json`, each with an mp3 in
`frontend/public/voice/` made once with Timbre v3.0. Lines built from what you said are spoken live.
After changing a line, delete its mp3 and run, from `backend/`:

```
.venv/bin/python scripts/make_voice_lines.py
```

## The recipe sheet

185 dishes that are in both the Indian Nutrient Databank and the Mendeley "6000+ Indian Food
Recipes" dataset. INDB gives the ingredients and nutrition; the method is adapted from Archana's
Kitchen via Mendeley and rewritten for Amma ji, with steps, timers, safety notes and common
mistakes in English, Hinglish, Hindi and Punjabi. Finding dishes from what you have runs in code,
with no AI calls.

- `data/amma_ji_recipes.xlsx` and `data/csv/`: the sheet as tables
- `backend/app/data/catalogue.json`: the same sheet as the server reads it
- `backend/scripts/steps/batch_*.json`: the written steps; edit these, then rebuild:

```
cd backend
.venv/bin/python scripts/build_catalogue.py
```

To put the sheet in Supabase: run `backend/supabase/schema.sql` once in the SQL editor, set
`SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in the environment, then run
`.venv/bin/python scripts/push_supabase.py` from `backend/`. Run it again after any rebuild.

## Folders

- `backend/app/`: the server (session state, Groq brain, Gnani ears and voice, pantry matching)
- `backend/scripts/`: builds the recipe sheet from INDB and Mendeley
- `backend/day1/`: the Day 1 feasibility tests
- `frontend/`: the React app (design notes in `frontend/DESIGN.md`)

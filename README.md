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
.venv/bin/uvicorn app.main:app --reload
```

Frontend (Node):

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, pick a language and tap "Start cooking". Tap the kadhai and talk.
Add `?dev` to the address to see how long each part of a turn takes.

## Folders

- `backend/app/`: the server (session state, Groq brain, Gnani ears and voice)
- `backend/day1/`: the Day 1 feasibility tests
- `frontend/`: the React app (design notes in `frontend/DESIGN.md`)

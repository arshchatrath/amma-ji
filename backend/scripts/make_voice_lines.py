"""Make the sound files for Amma ji's fixed lines (greetings, her questions) with Timbre v3.0.

The lines live in frontend/src/data/lines.json. Each becomes frontend/public/voice/<language>/<name>.mp3,
which the app plays straight away instead of asking Timbre every time. Run from the backend folder:

    .venv/Scripts/python scripts/make_voice_lines.py          (Windows; .venv/bin/python elsewhere)
    .venv/Scripts/python scripts/make_voice_lines.py --force  (remake all, e.g. after changing the voice)

Files that already exist are skipped, so after editing one line, delete its file and run again.
"""
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent.parent
FRONTEND = BACKEND.parent / "frontend"
load_dotenv(BACKEND / ".env")
URL = "https://api.vachana.ai/api/v1/tts/inference"
VOICE = os.getenv("TTS_VOICE", "Chetana")  # same voice as the live server
TTS_LANGUAGES = {"hi-en": "hi-en", "hi": "hi-IN", "pa": "pa-IN", "en": "en-IN"}


def main():
    key = os.getenv("GNANI_API_KEY") or sys.exit("GNANI_API_KEY missing (backend/.env or environment).")
    force = "--force" in sys.argv
    lines = json.loads((FRONTEND / "src" / "data" / "lines.json").read_text(encoding="utf-8"))
    made = skipped = 0
    for name, by_language in lines.items():
        for language, line in by_language.items():
            out = FRONTEND / "public" / "voice" / language / f"{name}.mp3"
            if out.exists() and not force:
                skipped += 1
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            body = {"text": line["say"], "model": "timbre-v3.0", "voice": VOICE,
                    "language": TTS_LANGUAGES[language], "speed": 1.0,
                    "audio_config": {"sample_rate": 24000, "num_channels": 1, "container": "mp3", "bitrate": "64k"}}
            for attempt in range(4):
                r = requests.post(URL, headers={"X-API-Key-ID": key}, json=body, timeout=60)
                if r.status_code != 429:
                    break
                time.sleep(1 + attempt)  # Gnani allows one voice request at a time
            if r.status_code != 200:
                sys.exit(f"{language}/{name}: Timbre said {r.status_code}: {r.text[:300]}")
            out.write_bytes(r.content)
            made += 1
            print(f"{language}/{name}.mp3  {len(r.content) // 1024} KB")
    print(f"Made {made}, skipped {skipped} that already existed.")


if __name__ == "__main__":
    main()

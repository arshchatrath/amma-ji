"""Day 1, step 1: does Timbre v3.0 work with our credits, and which voice is Amma ji?

Run from the backend folder:  python day1/tts_voices.py
Writes one WAV per voice per line into day1/out/voices/ and prints how long each took.
"""
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
API_KEY = os.getenv("GNANI_API_KEY")
if not API_KEY:
    sys.exit("GNANI_API_KEY missing. Copy backend/.env.example to backend/.env and fill it in.")

URL = "https://api.vachana.ai/api/v1/tts/inference"
VOICES = ["Kalpana", "Lakshmi", "Vasudha", "Chetana"]
LINES = {
    "sigh_fix": "<sigh> कोई बात नहीं बेटा। ढक्कन हटा के पाँच मिनट तेज़ आँच पे पकने दो, पानी सूख जाएगा।",
    "laugh_tease": "इतना कुछ घर पे है और तू बाहर से मंगवाने वाला था? <laugh> चल, टमाटर और मसाले हैं ना?",
}
OUT = Path(__file__).resolve().parent / "out" / "voices"
OUT.mkdir(parents=True, exist_ok=True)

for voice in VOICES:
    for name, text in LINES.items():
        start = time.perf_counter()
        r = requests.post(
            URL,
            headers={"X-API-Key-ID": API_KEY},
            json={
                "text": text,
                "model": "timbre-v3.0",
                "voice": voice,
                "language": "hi-en",
                "speed": 1.0,
                "audio_config": {"sample_rate": 24000, "num_channels": 1, "sample_width": 2,
                                 "encoding": "linear_pcm", "container": "wav"},
            },
            timeout=30,
        )
        ms = (time.perf_counter() - start) * 1000
        if r.status_code != 200:
            print(f"{voice:8} {name:12} FAILED {r.status_code}: {r.text[:300]}")
            continue
        path = OUT / f"{voice}_{name}.wav"
        path.write_bytes(r.content)
        print(f"{voice:8} {name:12} {ms:6.0f} ms  -> {path.name}")

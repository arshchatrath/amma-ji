"""Amma ji's ears and voice: Gnani Prisma STT and Timbre v3.0 streaming TTS.

The browser records WAV (mono, 16 kHz) itself, so the server needs no ffmpeg.
"""
import base64
import json
import os
import threading
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
STT_URL = "https://api.vachana.ai/stt/v3"
TTS_SSE_URL = "https://api.vachana.ai/api/v1/tts/sse"
VOICE = os.getenv("TTS_VOICE", "Chetana")
SAMPLE_RATE = 24000
# Separate open connections for ears and voice, so a cut-off voice stream never cools the STT line.
# A warm connection saves about half a second per STT call (1.0 s cold, 0.5 s warm on Day 1).
STT_HTTP = requests.Session()
TTS_HTTP = requests.Session()
# Gnani allows only one voice request at a time per account, so a new one cuts off the old one
_speaking = {"response": None}
_speaking_lock = threading.Lock()

# Session language -> Prisma STT code. Prisma has no Hinglish code; hi-IN did best on Day 1.
STT_CODES = {"hi-en": os.getenv("STT_CODE_HINGLISH", "hi-IN"), "hi": "hi-IN", "pa": "pa-IN", "en": "en-IN"}
# Session language -> Timbre language
TTS_LANGUAGES = {"hi-en": "hi-en", "hi": "hi-IN", "pa": "pa-IN", "en": "en-IN"}


class VoiceError(Exception):
    """Something went wrong with Gnani. The message is safe to show the user."""


def key():
    k = os.getenv("GNANI_API_KEY")
    if not k:
        raise VoiceError("The server has no GNANI_API_KEY set.")
    return k


def stt(wav_bytes, language):
    """Speech to text. Returns (transcript, ms)."""
    start = time.perf_counter()
    r = STT_HTTP.post(
        STT_URL,
        headers={"X-API-Key-ID": key()},
        files={"audio_file": ("audio.wav", wav_bytes, "audio/wav")},
        data={"language_code": STT_CODES[language], "format": "transcribe"},
        timeout=30,
    )
    ms = round((time.perf_counter() - start) * 1000)
    if r.status_code != 200:
        raise VoiceError(f"Gnani could not hear that ({r.status_code}). Try again.")
    return r.json().get("transcript", "").strip(), ms


def warm():
    """Open the STT connection early (at session start), so the first question is not slowed by it."""
    try:
        STT_HTTP.head("https://api.vachana.ai/", timeout=5)
    except requests.RequestException:
        pass


def tts_chunks(text, language, speed=1.0):
    """Streaming text to speech. Yields raw 16-bit PCM pieces (24 kHz mono) as Timbre makes them."""
    with _speaking_lock:
        if _speaking["response"] is not None:
            _speaking["response"].close()  # latest wins: stop the old voice stream
            _speaking["response"] = None
    body = {
        "text": text,
        "model": "timbre-v3.0",
        "voice": VOICE,
        "language": TTS_LANGUAGES[language],
        "speed": speed,
        "audio_config": {"sample_rate": SAMPLE_RATE, "num_channels": 1, "sample_width": 2,
                         "encoding": "linear_pcm", "container": "raw"},
    }
    for _ in range(4):
        r = TTS_HTTP.post(TTS_SSE_URL, headers={"X-API-Key-ID": key()}, json=body, stream=True, timeout=30)
        if r.status_code != 429:
            break
        r.close()
        time.sleep(0.25)  # Gnani may still count the stream we just cut off; give it a moment
    if r.status_code != 200:
        raise VoiceError(f"Amma ji lost her voice ({r.status_code}). Try again.")
    with _speaking_lock:
        _speaking["response"] = r
    try:
        event = None
        for line in r.iter_lines():
            line = line.decode("utf-8")
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:])
                if event == "error":
                    raise VoiceError("Amma ji lost her voice halfway. Try again.")
                if data.get("audio"):
                    yield base64.b64decode(data["audio"])
                if data.get("is_final"):
                    return
    except VoiceError:
        raise
    except Exception:
        if _speaking["response"] is r:
            raise  # a real failure
        return  # cut off by a newer voice request: stop quietly
    finally:
        r.close()
        with _speaking_lock:
            if _speaking["response"] is r:
                _speaking["response"] = None

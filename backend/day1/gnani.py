"""Small helpers for Gnani's ears (Prisma STT) and voice (Timbre v3.0 TTS), shared by the Day 1 scripts.

Each function returns (result, milliseconds) so every script can print how long each stage took.
"""
import base64
import io
import json
import os
import subprocess
import sys
import time
import wave
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
API_KEY = os.getenv("GNANI_API_KEY")
if not API_KEY:
    sys.exit("GNANI_API_KEY missing. Copy backend/.env.example to backend/.env and fill it in.")

STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
TTS_SSE_URL = "https://api.vachana.ai/api/v1/tts/sse"
# One session keeps the connection to Gnani open between calls, so only the first call pays for the
# secure handshake. Like staying on the phone instead of redialling for every sentence.
HTTP = requests.Session()


def to_wav16k(path):
    """Convert any phone recording (m4a, mp3, ogg, wav...) to WAV mono 16 kHz in memory with ffmpeg."""
    start = time.perf_counter()
    out = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", "16000",
         "-sample_fmt", "s16", "-f", "wav", "pipe:1"],
        capture_output=True, check=True,
    ).stdout
    return out, (time.perf_counter() - start) * 1000


def wav_seconds(wav_bytes):
    """Length of a 16 kHz mono 16-bit WAV, ignoring the 44-byte header."""
    return (len(wav_bytes) - 44) / (16000 * 2)


def stt(wav_bytes, language_code):
    """Speech to text. language_code is hi-IN (Devanagari output) or en-IN (Latin output), etc."""
    start = time.perf_counter()
    r = HTTP.post(
        STT_URL,
        headers={"X-API-Key-ID": API_KEY},
        files={"audio_file": ("audio.wav", wav_bytes, "audio/wav")},
        data={"language_code": language_code, "format": "transcribe"},
        timeout=60,
    )
    ms = (time.perf_counter() - start) * 1000
    if r.status_code != 200:
        raise RuntimeError(f"STT {r.status_code}: {r.text[:300]}")
    return r.json().get("transcript", ""), ms


def tts(text, voice, language="hi-en", speed=1.0):
    """Text to speech with Timbre v3.0. Returns WAV bytes (24 kHz mono)."""
    start = time.perf_counter()
    r = HTTP.post(
        TTS_URL,
        headers={"X-API-Key-ID": API_KEY},
        json={
            "text": text,
            "model": "timbre-v3.0",
            "voice": voice,
            "language": language,
            "speed": speed,
            "audio_config": {"sample_rate": 24000, "num_channels": 1, "sample_width": 2,
                             "encoding": "linear_pcm", "container": "wav"},
        },
        timeout=60,
    )
    ms = (time.perf_counter() - start) * 1000
    if r.status_code != 200:
        raise RuntimeError(f"TTS {r.status_code}: {r.text[:300]}")
    return r.content, ms


def tts_stream(text, voice, language="hi-en", speed=1.0, sample_rate=24000):
    """Streaming text to speech (SSE): audio arrives in small pieces while Timbre is still working.

    Returns (WAV bytes, ms until the first piece of audio, ms until the last piece).
    In the app, the first piece can start playing straight away.
    """
    start = time.perf_counter()
    r = HTTP.post(
        TTS_SSE_URL,
        headers={"X-API-Key-ID": API_KEY},
        json={
            "text": text,
            "model": "timbre-v3.0",
            "voice": voice,
            "language": language,
            "speed": speed,
            "audio_config": {"sample_rate": sample_rate, "num_channels": 1, "sample_width": 2,
                             "encoding": "linear_pcm", "container": "raw"},
        },
        stream=True,
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"TTS stream {r.status_code}: {r.text[:300]}")
    pcm, first_ms, event = bytearray(), None, None
    for line in r.iter_lines():
        line = line.decode("utf-8")
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data = json.loads(line[5:])
            if event == "error":
                raise RuntimeError(f"TTS stream error: {data}")
            if data.get("audio"):
                if first_ms is None:
                    first_ms = (time.perf_counter() - start) * 1000
                pcm += base64.b64decode(data["audio"])
            if data.get("is_final"):
                break
    total_ms = (time.perf_counter() - start) * 1000
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(bytes(pcm))
    return buf.getvalue(), first_ms, total_ms

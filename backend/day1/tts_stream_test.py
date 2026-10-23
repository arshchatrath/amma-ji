"""Day 1, step 4 helper: how soon does Amma ji start speaking? Full file (REST) vs streaming (SSE).

Run from the backend folder:  python day1/tts_stream_test.py Chetana
Speaks the two test lines 3 times each both ways and prints the time to the first sound.
Saves the streamed audio to day1/out/stream/ so you can check it sounds the same.
"""
import sys
from pathlib import Path

from gnani import tts, tts_stream

VOICE = sys.argv[1] if len(sys.argv) > 1 else "Chetana"
LINES = {
    "sigh_fix": "<sigh> कोई बात नहीं बेटा। ढक्कन हटा के पाँच मिनट तेज़ आँच पे पकने दो, पानी सूख जाएगा।",
    "laugh_tease": "इतना कुछ घर पे है और तू बाहर से मंगवाने वाला था? <laugh> चल, टमाटर और मसाले हैं ना?",
}
OUT = Path(__file__).resolve().parent / "out" / "stream"
OUT.mkdir(parents=True, exist_ok=True)

rest, first, done = [], [], []
for round_ in range(1, 4):
    for name, text in LINES.items():
        _, rest_ms = tts(text, VOICE)
        audio, first_ms, total_ms = tts_stream(text, VOICE)
        (OUT / f"{VOICE}_{name}.wav").write_bytes(audio)
        rest.append(rest_ms)
        first.append(first_ms)
        done.append(total_ms)
        print(f"round {round_} {name:12} full file {rest_ms:5.0f} ms | stream: first sound {first_ms:5.0f} ms, "
              f"all done {total_ms:5.0f} ms")


def median(xs):
    return sorted(xs)[len(xs) // 2]


print(f"\n{VOICE} median time to first sound: full file {median(rest):.0f} ms, streaming {median(first):.0f} ms")

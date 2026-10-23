"""Day 1, step 2: which Prisma STT language code hears Hinglish quantities better, hi-IN or en-IN?

Put your phone recordings in backend/day1/recordings/ (any of m4a, mp3, ogg, wav, aac, flac).
Optional: add backend/day1/recordings/expected.json with what you actually said, like
    {"q01.m4a": "Amma ji, do chammach namak daal doon?"}
so the script can score how many quantity words each code caught.

Run from the backend folder:  python day1/stt_compare.py   (or add a folder: python day1/stt_compare.py some/folder)
Prints both transcripts per recording and saves everything to day1/out/stt_results.json.
"""
import json
import sys
from pathlib import Path

from gnani import stt, to_wav16k, wav_seconds
from quantities import quantities

DAY1 = Path(__file__).resolve().parent
RECORDINGS = Path(sys.argv[1]) if len(sys.argv) > 1 else DAY1 / "recordings"
OUT = DAY1 / "out"
CODES = ["hi-IN", "en-IN"]
AUDIO = {".m4a", ".mp3", ".ogg", ".wav", ".aac", ".flac", ".opus", ".webm"}

files = sorted(p for p in RECORDINGS.glob("*") if p.suffix.lower() in AUDIO) if RECORDINGS.exists() else []
if not files:
    raise SystemExit(f"No recordings found. Put your phone recordings in {RECORDINGS}")
expected_file = RECORDINGS / "expected.json"
expected = json.loads(expected_file.read_text(encoding="utf-8")) if expected_file.exists() else {}

results = []
score = {c: [0, 0] for c in CODES}  # quantity words caught, quantity words said
time_ms = {c: [] for c in CODES}
for path in files:
    wav, convert_ms = to_wav16k(path)
    secs = wav_seconds(wav)
    print(f"\n{path.name}  ({secs:.1f} s audio, convert {convert_ms:.0f} ms)")
    if secs > 30:
        print("  warning: over 30 s, the STT may reject it")
    said = expected.get(path.name)
    if said:
        print(f"  said    : {said}")
    row = {"file": path.name, "said": said, "audio_s": round(secs, 1), "convert_ms": round(convert_ms)}
    for code in CODES:
        try:
            text, ms = stt(wav, code)
        except Exception as e:
            print(f"  {code}   : FAILED {e}")
            row[code] = {"error": str(e)}
            continue
        time_ms[code].append(ms)
        caught = quantities(text)
        line = f"  {code}   : {text}  [{ms:.0f} ms]"
        if said:
            wanted = quantities(said)
            hits = len(wanted & caught)
            score[code][0] += hits
            score[code][1] += len(wanted)
            line += f"  quantities {hits}/{len(wanted)}"
        print(line)
        row[code] = {"transcript": text, "ms": round(ms), "quantities": sorted(caught)}
    results.append(row)

print("\nSummary")
for code in CODES:
    if time_ms[code]:
        avg = sum(time_ms[code]) / len(time_ms[code])
        line = f"  {code}: average {avg:.0f} ms over {len(time_ms[code])} recordings"
        if score[code][1]:
            line += f", quantity words caught {score[code][0]}/{score[code][1]}"
        print(line)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "stt_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved {OUT / 'stt_results.json'}")

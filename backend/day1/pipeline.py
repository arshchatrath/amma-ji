"""Day 1, step 4: the whole loop, timed. Recording -> WAV -> Prisma STT -> Groq -> Timbre v3.0.

The question this answers (brief section 9): does Amma ji's reply start within ~3 seconds,
with quantities heard correctly? Go/no-go line is ~4 seconds.

Uses the same recordings (and optional expected.json) as step 2, in backend/day1/recordings/.
Run from the backend folder:
    python day1/pipeline.py --stt en-IN --model openai/gpt-oss-120b --voice Chetana
Saves Amma ji's spoken replies to day1/out/pipeline/ and the timings to day1/out/pipeline_results.json.
"""
import argparse
import json
from pathlib import Path

from brain import ask_groq, check_reply
from gnani import stt, to_wav16k, tts_stream
from quantities import quantities

parser = argparse.ArgumentParser()
parser.add_argument("--stt", default="en-IN", help="Prisma language code: en-IN or hi-IN")
parser.add_argument("--model", default="openai/gpt-oss-120b", help="Groq model id")
parser.add_argument("--voice", default="Chetana", help="Timbre v3.0 voice (Chetana is Amma ji)")
parser.add_argument("--language", default="hi-en", help="Session language: hi-en, hi, pa or en")
parser.add_argument("--recordings", help="Folder of recordings (default day1/recordings)")
args = parser.parse_args()

DAY1 = Path(__file__).resolve().parent
RECORDINGS = Path(args.recordings) if args.recordings else DAY1 / "recordings"
OUT = DAY1 / "out"
AUDIO = {".m4a", ".mp3", ".ogg", ".wav", ".aac", ".flac", ".opus", ".webm"}
files = sorted(p for p in RECORDINGS.glob("*") if p.suffix.lower() in AUDIO) if RECORDINGS.exists() else []
if not files:
    raise SystemExit(f"No recordings found. Put your phone recordings in {RECORDINGS}")
expected_file = RECORDINGS / "expected.json"
expected = json.loads(expected_file.read_text(encoding="utf-8")) if expected_file.exists() else {}
(OUT / "pipeline").mkdir(parents=True, exist_ok=True)

print(f"STT {args.stt} | Groq {args.model} | voice {args.voice} | language {args.language}")
rows = []
for path in files:
    print(f"\n{path.name}")
    row = {"file": path.name, "said": expected.get(path.name)}
    try:
        wav, convert_ms = to_wav16k(path)
        transcript, stt_ms = stt(wav, args.stt)
        brain = ask_groq(transcript, args.model, args.language)
        if "error" in brain:
            raise RuntimeError(f"Groq {brain['error']}")
        # Streaming: Amma ji can start speaking as soon as the first piece arrives, so that is what we time.
        audio, tts_ms, tts_done_ms = tts_stream(brain["reply"], args.voice, args.language)
    except Exception as e:
        print(f"  FAILED {e}")
        rows.append({**row, "error": str(e)})
        continue
    total = convert_ms + stt_ms + brain["ms"] + tts_ms
    (OUT / "pipeline" / f"{path.stem}_reply.wav").write_bytes(audio)
    if row["said"]:
        print(f"  said       : {row['said']}")
    print(f"  heard      : {transcript}")
    if row["said"]:
        wanted = quantities(row["said"])
        row["quantities_ok"] = wanted <= quantities(transcript)
        print(f"  quantities : {'all heard' if row['quantities_ok'] else 'MISSED some'} "
              f"(said {sorted(wanted)}, heard {sorted(quantities(transcript))})")
    problems = check_reply(brain["reply"], args.language)
    print(f"  tool       : {brain['tool']} {json.dumps(brain['args'], ensure_ascii=False)}")
    print(f"  reply      : {brain['reply']}" + (f"   problems: {', '.join(problems)}" if problems else ""))
    print(f"  ms         : convert {convert_ms:.0f} + STT {stt_ms:.0f} + Groq {brain['ms']:.0f} "
          f"+ TTS first sound {tts_ms:.0f} = {total:.0f} to first audio")
    rows.append({**row, "transcript": transcript, "tool": brain["tool"], "args": brain["args"],
                 "reply": brain["reply"], "problems": problems, "convert_ms": round(convert_ms),
                 "stt_ms": round(stt_ms), "groq_ms": round(brain["ms"]), "tts_ms": round(tts_ms),
                 "total_ms": round(total)})

done = [r for r in rows if "error" not in r]
print("\nSummary")
if done:
    totals = sorted(r["total_ms"] for r in done)
    median = totals[len(totals) // 2]
    for stage in ("convert_ms", "stt_ms", "groq_ms", "tts_ms"):
        times = sorted(r[stage] for r in done)
        print(f"  {stage[:-3]:8}: median {times[len(times) // 2]} ms, slowest {times[-1]} ms")
    print(f"  total   : median {median} ms, slowest {totals[-1]} ms")
    print(f"  under 3 s: {sum(t < 3000 for t in totals)}/{len(done)}, over 4 s: {sum(t > 4000 for t in totals)}/{len(done)}")
    scored = [r for r in done if "quantities_ok" in r]
    if scored:
        print(f"  quantities fully heard: {sum(r['quantities_ok'] for r in scored)}/{len(scored)}")
    print("  verdict : " + ("GO (median under 4 s)" if median <= 4000 else "NO-GO (median over 4 s), stop and rethink"))
print(f"  failed  : {len(rows) - len(done)}/{len(rows)}")
(OUT / "pipeline_results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved replies to {OUT / 'pipeline'} and timings to {OUT / 'pipeline_results.json'}")

"""Day 1, step 3: which Groq model makes the better Amma ji brain?

Sends 12 typed cooking-mode sentences (Hinglish in English letters like en-IN STT gives, Hindi in
Devanagari like hi-IN STT gives, plus Punjabi and English) to each model with the fake dal tadka
state. For each one, checks: did it pick the right tool, did the reply follow Amma ji's rules,
how many ms it took.

Run from the backend folder:
    python day1/groq_compare.py                       (compares the two default models)
    python day1/groq_compare.py openai/gpt-oss-120b   (one model, or any list of model ids)
Saves everything to day1/out/groq_results.json.
"""
import json
import sys
from pathlib import Path

from brain import ask_groq, check_reply

MODELS = sys.argv[1:] or ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
OUT = Path(__file__).resolve().parent / "out"

# (what the user said, session language, tools that count as correct)
CASES = [
    ("Amma ji maine paani zyada daal diya", "hi-en", ["fix_mistake"]),
    ("agla step batao", "hi-en", ["next_step"]),
    ("ek baar phir se bolo, dheere dheere", "hi-en", ["repeat_step"]),
    ("haldi daal di", "hi-en", ["mark_added"]),
    ("ghee nahi hai, kya use karun?", "hi-en", ["substitute"]),
    ("pandrah minute ka timer laga do", "hi-en", ["start_timer"]),
    ("timer mein kitna time bacha hai?", "hi-en", ["check_timer"]),
    ("do chammach namak daal doon?", "hi-en", ["answer_question"]),
    ("मेरे पास सिर्फ दस मिनट हैं", "hi", ["shorten_time"]),
    ("दाल बहुत तीखी हो गई", "hi", ["adjust_spice", "fix_mistake"]),
    ("ਲੂਣ ਜ਼ਿਆਦਾ ਹੋ ਗਿਆ", "pa", ["fix_mistake"]),
    ("what was the previous step again?", "en", ["previous_step"]),
]

results = {}
for model in MODELS:
    print(f"\n=== {model}")
    rows = []
    for text, language, wanted in CASES:
        out = ask_groq(text, model, language)
        if "error" in out:
            print(f"  [{language}] {text}\n    FAILED {out['error']}")
            rows.append({"text": text, "language": language, **out})
            continue
        right_tool = out["tool"] in wanted
        problems = check_reply(out["reply"], language)
        if out["extra_calls"]:
            problems.append(f"{out['extra_calls']} extra tool calls")
        mark = "ok " if right_tool and not problems else "BAD"
        print(f"  {mark} [{language}] {text}")
        print(f"    tool  : {out['tool']} {json.dumps(out['args'], ensure_ascii=False)}"
              f"{'' if right_tool else '  (wanted ' + ' or '.join(wanted) + ')'}")
        print(f"    reply : {out['reply']}")
        print(f"    {out['ms']:.0f} ms" + (f"   problems: {', '.join(problems)}" if problems else ""))
        rows.append({"text": text, "language": language, "wanted": wanted, "right_tool": right_tool,
                     "problems": problems, **out})
    results[model] = rows

print("\nSummary")
for model, rows in results.items():
    done = [r for r in rows if "error" not in r]
    if not done:
        print(f"  {model}: every call failed")
        continue
    times = sorted(r["ms"] for r in done)
    tokens = sum(r["usage"].get("total_tokens", 0) for r in done)
    print(f"  {model}")
    print(f"    right tool     : {sum(r['right_tool'] for r in done)}/{len(CASES)}")
    print(f"    rules followed : {sum(not r['problems'] for r in done)}/{len(CASES)}")
    print(f"    failed calls   : {len(rows) - len(done)}")
    print(f"    time           : median {times[len(times) // 2]:.0f} ms, slowest {times[-1]:.0f} ms")
    print(f"    tokens used    : {tokens} total, about {tokens // len(done)} per turn")
    print(f"    rate limits    : {json.dumps(done[-1]['limits'])}")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "groq_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved {OUT / 'groq_results.json'}")

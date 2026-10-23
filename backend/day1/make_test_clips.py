"""Stand-in recordings until the real phone ones arrive: Timbre speaks 10 cooking questions as the "user".

Makes day1/out/test_clips/clean/ and day1/out/test_clips/noisy/ (same clips with fan-like noise),
each with an expected.json, so stt_compare.py and pipeline.py can run on them:
    python day1/make_test_clips.py
    python day1/stt_compare.py day1/out/test_clips/noisy
This is a warm-up only. Synthetic speech is cleaner than a real person 1.5 m from the phone.
"""
import json
import subprocess
from pathlib import Path

from gnani import tts

USER_VOICE = "Shubham"  # a male voice, so the "user" does not sound like Amma ji
# (what Timbre reads, in Devanagari so it pronounces it well; what was "said", as en-IN would write it)
QUESTIONS = [
    ("अम्मा जी, दो चम्मच नमक डाल दूँ?", "Amma ji, do chammach namak daal doon?"),
    ("आधा कप पानी और डालूँ क्या?", "aadha cup paani aur daaloon kya?"),
    ("मैंने एक चम्मच लाल मिर्च डाल दी, ज़्यादा तो नहीं?", "maine ek chammach laal mirch daal di, zyada to nahi?"),
    ("पंद्रह मिनट का टाइमर लगा दो।", "pandrah minute ka timer laga do"),
    ("अम्मा जी, मैंने पानी ज़्यादा डाल दिया।", "Amma ji, maine paani zyada daal diya"),
    ("डेढ़ कप दाल के लिए कितना पानी चाहिए?", "dedh cup daal ke liye kitna paani chahiye?"),
    ("एक चुटकी हींग डालूँ?", "ek chutki hing daaloon?"),
    ("दो गिलास पानी कुकर में डाल दिया।", "do glass paani cooker mein daal diya"),
    ("तीन सीटी के बाद गैस बंद करूँ?", "teen seeti ke baad gas band karoon?"),
    ("आधा चम्मच हल्दी काफ़ी है?", "aadha chammach haldi kaafi hai?"),
]

OUT = Path(__file__).resolve().parent / "out" / "test_clips"
clean, noisy = OUT / "clean", OUT / "noisy"
clean.mkdir(parents=True, exist_ok=True)
noisy.mkdir(parents=True, exist_ok=True)
expected = {}
for i, (text, said) in enumerate(QUESTIONS, 1):
    name = f"q{i:02}.wav"
    audio, ms = tts(text, USER_VOICE, "hi-en")
    (clean / name).write_bytes(audio)
    # Brown noise sounds like a fan or exhaust. Mixed in at a level that is clearly audible.
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", str(clean / name),
         "-f", "lavfi", "-i", "anoisesrc=color=brown:amplitude=0.25",
         "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:normalize=0", str(noisy / name)],
        check=True,
    )
    expected[name] = said
    print(f"{name}  {ms:5.0f} ms  {said}")
for folder in (clean, noisy):
    (folder / "expected.json").write_text(json.dumps(expected, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved to {clean} and {noisy}")

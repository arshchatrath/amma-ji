# Project Brief: Amma ji, a voice that cooks with you

Entry for Gnani AI's Great Indian AI Internship Challenge.
Deadline: **November 10, 2026, 11:59 PM IST.** Today: Oct 23. About 18 days.

---

## 0. How to work with me (read first, Claude Code)

- I'm learning. Explain everything you do in **very simple terms** with everyday analogies
- **Build step by step.** After each step: tell me what changed, which files, and how to test it. Wait for me before the next step
- **Iterate, don't rewrite.** Small, targeted changes
- **Day 1 is a test, not the app** (section 9). Don't build UI until the test passes
- No emojis anywhere (UI, code comments, docs). No em dashes in UI copy
- For any design/UI work, use my locally saved design skills in `~/.claude/skills` (e.g. `design-taste-frontend`, `high-end-visual-design`, `anatomy`) plus the `frontend-design` skill if available
- Keep all API keys in `.env` on the backend. Never in the browser, never committed
- If you're unsure whether an API supports something, check the docs and tell me. Don't guess

---

## 1. One-line pitch

**Amma ji is a voice cooking companion that talks to you in your language, knows which step you're on, catches your mistakes, fixes them, and teases you a little.**

Not a recipe app. A voice in your kitchen.

### Who it's for
Young people living away from home (hostels, PGs, first jobs) who know what ghar ka khana tastes like but not how to make it.

### The wow moment (build everything around this)
> You: "Amma ji, maine paani zyada daal diya."
> Amma ji: *(sighs)* "Koi baat nahi beta. Dhakkan hata ke 5 minute tez aanch pe pakne do, paani sukh jayega."

She knows it's dal, it's step 4, and what to do. In Hinglish, with a real sigh (Gnani Timbre v3 audio tags).

---

## 2. Stack (decided)

| Part | Choice | Role |
|---|---|---|
| Frontend | React + Vite, as a **PWA** (web only, installable from browser) | UI, mic, playback |
| Hosting | Vercel (free HTTPS, needed for mic) | |
| Backend | Python FastAPI on Render/Railway | Keeps keys safe, orchestrates the loop |
| Ears | **Gnani STT (Prisma)** | Speech to text |
| Brain | **Groq** (a model that supports tool use / function calling) | Understands, decides, writes reply |
| Voice | **Gnani TTS, Timbre v3.0** | Text to expressive speech |
| Wake word | **Picovoice Porcupine Web SDK**, phrase "Amma ji" | Runs in the browser, no audio sent |
| Data | 20-25 hand-written recipe JSON files + INDB nutrition | |
| Auth/DB (later, optional) | Supabase | Only if time allows |

**No** vector DB, no agent frameworks, no LangChain. Plain function calling.

---

## 3. API reference (verify exact params in docs before coding)

### Gnani STT
- `POST https://api.vachana.ai/stt/v3`
- Header: `X-API-Key-ID: <GNANI_API_KEY>`
- Form fields: `audio_file`, `language_code` (e.g. `hi-IN`, `pa-IN`, `en-IN`; check Hinglish code in docs), `format=transcribe`
- Send audio as **WAV, mono, 16kHz** (convert from browser webm/opus on the backend with ffmpeg)
- WebSocket streaming also exists (sub-200ms); start with REST, move to streaming only if latency needs it
- Docs: https://docs.gnani.ai

### Gnani TTS (Timbre)
- `POST https://api.vachana.ai/api/v1/tts/inference` (full audio in one response). SSE and WebSocket streaming also exist
- Model: **`timbre-v3.0`** (each v3.0 voice speaks all 10 languages; supports audio tags)
- v3.0 voices: Avinash, Shivani, Lakshmi, Kalpana, Shubham, Prakash, Devansh, Yashraj, Chetana, Vasudha, Riyaa, Tarika, Harshad. **Pick a warm, older-sounding female voice for Amma ji** (test Kalpana, Lakshmi, Vasudha, Chetana)
- Languages: `hi-IN`, `en-IN`, `ta-IN`, `te-IN`, `kn-IN`, `ml-IN`, `mr-IN`, `pa-IN`, `bn-IN`, `gu-IN`, Hinglish `hi-en`, or `auto`
- Audio tags (v3.0 only): `<laugh>`, `<sigh>`, `<excited>`, `<slow>`, `<pauses>`, `<whispers>`, etc.
- `speed`: 0.85 to 1.15
- Formats: wav, mp3, ogg and more; sample rates 8k to 48k
- Confirm on day 1 that Timbre v3.0 calls work with my programme credits

### Groq
- Use a model that supports **tool use**. Compare 2 candidates on: Hindi/Hinglish/Punjabi quality, tool-call reliability, speed
- Use **streaming**: send the first full sentence to TTS as soon as it's ready
- Check free-tier rate limits (requests/min, tokens/day) and log usage

### Picovoice Porcupine (Web)
- Train "Amma ji" in Picovoice Console (English model; no Indian-language model is listed), download the Web model
- Needs an AccessKey. It's visible in the browser, so check Picovoice's free-tier limits and web guidance
- Runs fully in the browser; no audio leaves the device until after the wake word

---

## 4. Amma ji's voice and personality

### Rules for every reply (put these in the Groq system prompt)
- **1-2 short sentences.** People are cooking, not reading
- Hindi in **Devanagari**, Punjabi in **Gurmukhi**, or Hinglish for mixed. No romanized Hindi (TTS mispronounces it)
- Warm, caring, lightly teasing. Calls the user "beta"
- **At most one audio tag per reply**, only where it fits (`<sigh>` for mistakes, `<laugh>` for jokes)
- Tease about **cooking only**. Never about weight, looks, eating habits, money or anything personal
- Supportive when the user makes a mistake
- Cooking instructions always beat jokes
- Never invent outcomes. If unsure, say so and suggest the safe option
- One setting: **"Less teasing"** toggle (plain, practical tone)

### Example
> User: "I have paneer, potatoes, onions, and curd. Give me something quick."
> Amma ji: "Itna kuch ghar pe hai aur tu bahar se mangwane wala tha? `<laugh>` Chal, tamatar aur masale hain na?"

---

## 5. User flows (MVP)

### Flow A: Start
1. Pick language (start with **Hindi, Hinglish, Punjabi, English**; add more only after testing STT for them)
2. Tap **"Start cooking"** (this tap also unlocks browser audio)

### Flow B: Tell her what you have
1. Speak naturally: "Do aloo, paneer, thoda pyaaz, dahi hai. 20 minute mein kuch bana do."
2. Backend: STT, then Groq extracts ingredients, quantities (if said), time limit, diet, allergies
3. Normalize names via a synonym file (aloo = potato = batata)
4. Show the extracted list as chips; user can correct by voice or tap
5. Ask a follow-up only if it changes the result ("Tamatar hai?")

### Flow C: Pick a dish
1. Rank recipes **in code** (not the LLM): ingredient match, missing essentials, time, diet, allergies
2. Show top 3, each labelled:
   - **Can make now**
   - **Needs 1 optional item**
   - **Missing an essential** (never call this "ready")
3. One-line "why this fits" per dish (LLM writes it from the ranking result)
4. User picks by voice ("doosra wala") or tap

### Flow D: Recipe card
Name, servings, prep/cook time, ingredients with quantities, steps, substitutions, nutrition per serving (from INDB, labelled "estimate"), source note.

### Flow E: Cooking mode (the core)
- Screen: big current step, step number, active timers, mic status, Stop/Mute buttons
- Amma ji reads the step aloud
- User says **"Amma ji, ..."** or taps the mic button
- Supported intents (as Groq tools):
  - `next_step`, `previous_step`, `repeat_step(slow: bool)`
  - `mark_added(ingredient)`
  - `substitute(ingredient)` (only from the recipe's substitution list; otherwise say it's untested)
  - `fix_mistake(description)` (uses the recipe's `common_mistakes` first)
  - `adjust_spice(direction)`
  - `start_timer(minutes, label)`, `check_timer`
  - `shorten_time(minutes_available)`
  - `answer_question(text)` for anything else, grounded in current recipe and step
- After replying, go back to wake-word listening
- **Timers run in code**, never "remembered" by the LLM

### Flow F: Finish
Summary: what you made, substitutions, nutrition per serving (estimate), optional "how was it?"

---

## 6. Data

### Recipes: write our own, small and structured
- **20-25 everyday dishes**: dal tadka, aloo sabzi, paneer bhurji, poha, upma, khichdi, rajma, chole, aloo paratha, jeera rice, egg bhurji, maggi upgrade, curd rice, besan chilla, bhindi, etc.
- **Steps written in our own words** (don't copy recipe websites)
- Ingredient quantities and nutrition from **INDB** (Indian Nutrient Databank) where available. Check the INDB GitHub repo licence first and credit it
- **Do NOT ship** the Mendeley "6000+ Indian recipes" dataset (scraped from Archana's Kitchen). OK only for private testing of the matcher

### Recipe JSON schema (starting point)
```json
{
  "id": "dal_tadka",
  "name": {"en": "Dal Tadka", "hi": "दाल तड़का", "pa": "ਦਾਲ ਤੜਕਾ"},
  "cuisine": "North Indian",
  "diet": ["vegetarian", "jain_possible"],
  "allergens": [],
  "servings": 2,
  "prep_min": 10,
  "cook_min": 25,
  "equipment": ["pressure cooker"],
  "ingredients": [
    {"id": "toor_dal", "qty": 100, "unit": "g", "essential": true},
    {"id": "onion", "qty": 1, "unit": "medium", "essential": false},
    {"id": "garam_masala", "qty": 0.5, "unit": "tsp", "essential": false,
     "substitutes": ["kitchen_king", "skip"]}
  ],
  "steps": [
    {"n": 1, "text": {"en": "...", "hi": "..."}, "uses": ["toor_dal"],
     "timer_min": null, "safety": null},
    {"n": 4, "text": {"en": "..."}, "uses": [], "timer_min": 15,
     "safety": "Let the pressure release fully before opening the cooker."}
  ],
  "common_mistakes": [
    {"mistake": "too much water", "fix": {"en": "...", "hi": "..."}},
    {"mistake": "too salty", "fix": {"en": "..."}}
  ],
  "nutrition_per_serving": {"kcal": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fibre_g": 0,
                            "source": "INDB", "is_estimate": true},
  "source_note": "Steps written by the Amma ji team. Nutrition: INDB."
}
```

### Ingredient synonyms
`data/ingredients.json`: canonical id, names in each language, common spellings (aloo, aalu, potato, batata).

---

## 7. Session state (one object per session, sent to Groq every turn)

```json
{
  "session_id": "...",
  "language": "hi-en",
  "teasing": true,
  "recipe_id": "dal_tadka",
  "servings": 2,
  "current_step": 4,
  "completed_steps": [1, 2, 3],
  "ingredients_added": ["toor_dal", "water"],
  "substitutions": [{"from": "garam_masala", "to": "kitchen_king"}],
  "quantity_changes": [],
  "allergies": ["peanut"],
  "timers": [{"label": "pressure cook", "ends_at": "ISO time"}],
  "open_questions": [],
  "history_summary": "short running summary, not full transcript"
}
```

- State lives on the backend (in memory or SQLite for MVP), keyed by session id
- **Allergies filter recipes in code.** Never rely on the LLM to remember
- Keep only a short summary of past turns, not the full transcript

---

## 8. Voice loop details (where it usually breaks)

1. **Wake word:** Porcupine listens for "Amma ji" in the browser during cooking mode only
2. **Record command** after wake word until ~1s of silence (or tap to stop)
3. Backend: convert to WAV mono 16kHz, then Gnani STT, then Groq (with state + tools), then Timbre v3, then stream audio back
4. **While Amma ji is speaking, pause wake-word detection** so she doesn't wake herself. Keep browser echo cancellation on
5. **Interruptions:** big Stop button always visible; if possible, "Amma ji, ruko" stops playback
6. **Confirm risky quantities:** for salt, chilli, water, oil, repeat back ("Do chammach namak, theek?")
7. **Fallbacks:** if wake word unavailable or unreliable, use push-to-talk button. Button is always available anyway
8. Screen Wake Lock on during cooking mode; show "Keep this screen open while cooking"
9. Log timings for every step (STT ms, Groq ms, TTS first-audio ms) in dev mode

### Privacy (show in UI)
"Amma ji listens for her name on your device. Only what you say after 'Amma ji' is sent to Gnani to understand you. No recordings are saved."
- Don't store raw audio anywhere
- Clear mic indicator whenever the mic is active, plus Mute and Stop

---

## 9. Day 1: feasibility test (do this BEFORE any UI)

Build a bare script/endpoint, no UI. Test the riskiest assumption:

> Speak a Hinglish cooking question from 1-1.5 m away with a fan or cooker running. Does Amma ji's reply start **within ~3 seconds**, with quantities transcribed correctly?

Test steps:
1. Record 10 sample questions on my phone (I'll provide), including quantities ("do chammach", "aadha cup") and noise
2. For each: convert, Gnani STT, Groq (with a fake recipe state + tools), Timbre v3.0
3. Report per sample: transcript, correct or not, tool chosen, reply text, and **time for each stage + total time to first audio**
4. Try 2 Groq models and compare
5. Try 3-4 Timbre v3.0 voices for Amma ji; save samples so I can pick
6. Confirm Timbre v3.0 works with my credits

Also test Picovoice "Amma ji":
- 20 tries from different spots: count misses (target 18+/20)
- 15 minutes of normal chatter/TV: count false wakes (target 0-1)

**Go/no-go:** if total time is usually over ~4s or quantities are often wrong, stop and tell me before building further.

---

## 10. Build order

| Days | Dates | Work |
|---|---|---|
| 1-2 | Oct 23-24 | Day-1 test (section 9), pick Groq model and Amma ji voice |
| 3-5 | Oct 25-27 | 20-25 recipe JSONs, ingredient synonyms, matching and ranking |
| 6-9 | Oct 28-31 | Cooking-mode loop: state, Groq tools, push-to-talk, timers |
| 10-11 | Nov 1-2 | Personality, Timbre tags, language picker, "less teasing" toggle |
| 12-13 | Nov 3-4 | Picovoice "Amma ji", mic indicator, mute/stop, self-wake protection |
| 14-15 | Nov 5-6 | UI polish, PWA, test with 3-5 friends actually cooking |
| 16-18 | Nov 7-10 | Demo video, LinkedIn/X post, push engagement, submit |

If behind: cut nutrition display, extra languages, then wake word (keep push-to-talk). **Never cut the cooking-mode wow moment.**

---

## 11. Scope

### Must-have
- Language pick (Hindi, Hinglish, Punjabi, English)
- Voice ingredient entry with correction
- Ranked dishes with honest labels
- Recipe card with steps, substitutions, nutrition estimate
- Cooking mode with session state, tools, timers, push-to-talk
- Amma ji's voice with Timbre v3 tags
- Stop/mute, mic indicator, privacy note
- PWA, works on Android Chrome

### Should-have
- "Amma ji" wake word
- "Less teasing" toggle
- Spoken dish choice ("doosra wala")
- More languages after testing

### Not in MVP
Camera pantry scan, cooking-sound recognition, recipe scraping, social, grocery delivery, meal planning, medical/therapeutic nutrition, always-on listening, arbitrary custom wake words, multiple personalities, memory across sessions, native app.

---

## 12. Safety and trust

- **Allergies:** asked at start, filtered in code, re-checked before suggesting any substitution
- **Food safety notes** written into recipe steps (pressure cooker release, cooking rajma fully, chicken cooked through)
- **Substitutions:** only from the recipe's list; anything else gets "I haven't tested that, try at your own risk" style wording
- **Nutrition:** always labelled "estimate", from INDB, never generated by the LLM; no medical or health claims
- **Ambiguity:** ask instead of guess when it matters (quantities, allergens, heat)
- **Language claims:** only list languages actually tested

---

## 13. Design direction

Use my design skills (`~/.claude/skills`: `design-taste-frontend`, `high-end-visual-design`, `anatomy`) to define the look. Constraints:
- **Readable from across the kitchen:** huge current-step text, high contrast, large tap targets (messy hands)
- Warm, homely, modern, not cartoonish. Think haldi, terracotta, steel, warm paper
- Cooking mode is distraction-free: one step, timers, mic state, Stop
- Mobile-first, no horizontal scroll, WCAG AA contrast
- No emojis. Minimal animation (a gentle "listening" indicator is fine)
- Define colours as CSS variables in one place

---

## 14. Contest rules that matter

- Must genuinely use Gnani: **Prisma STT + Timbre v3.0 TTS**. Name them in the submission
- Demo video posted on LinkedIn/X with `#GnaniAI` `#GreatIndianAIInternshipChallenge`, tagging Gnani AI, **live before submitting**
- **Shortlist = verified engagement** on the post. Interview decides the offer
- No bought engagement, bots, engagement swaps, plagiarism or **misleading demos**: record a real cooking session
- Synthetic/own data only
- Awards to target: **Mixed Vibes** (Hinglish), **Real Deal**, **Demo Day Drop**, Solo Ninja (if solo)

---

## 15. Demo video (60 seconds)

1. Hook (0-5s): hostel kitchen, "Ghar ka khana yaad aata hai?"
2. Ingredients (5-15s): "Amma ji, do aloo, paneer, pyaaz hai." Three dishes appear
3. Cooking (15-40s): steps read aloud, a timer starts, then "Amma ji, paani zyada ho gaya" and she sighs and fixes it
4. Tease (40-48s): one light, funny line
5. Tech (48-55s): "Powered by Gnani's Prisma STT and Timbre v3.0"
6. CTA (55-60s): link, tags, hashtags

---

## 16. Links

- Contest: https://www.gnani.ai/internship
- Gnani docs: https://docs.gnani.ai
- Gnani TTS docs: https://docs.gnani.ai/api/TTS/tts-inference.md
- Gnani dashboard: https://app.gnani.ai/voice
- Groq console/docs: https://console.groq.com
- Picovoice Porcupine: https://picovoice.ai/docs/porcupine/
- Picovoice custom wake words (web): https://picovoice.ai/blog/how-to-add-custom-wake-words-to-any-web-app
- INDB paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC11277795

"""Amma ji's brain: one Groq call per turn that picks a tool and writes what she says.

Compared with the Day 1 test, each turn sends a short plain-text note (only the steps around the
current one, safe substitutes, what is already in the pot) instead of the whole recipe as JSON,
so more turns fit in Groq's free limit.
"""
import json
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from .session import RECIPES, in_language, ingredient_name, live_timers, normalise, step_text

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
HTTP = requests.Session()  # keeps the connection to Groq open between turns

LANGUAGE_RULES = {
    "hi": "Reply in Hindi written in Devanagari.",
    "hi-en": "Reply in Hinglish: Hindi words in Devanagari, common English words (cooker, timer, ok) may "
             "stay in English letters. Never write Hindi words in English letters.",
    "pa": "Reply in Punjabi written in Gurmukhi.",
    "en": "Reply in simple Indian English, in English letters. Only the word बेटा stays in Devanagari.",
}

RULES = """You are Amma ji, a warm Indian mother helping the user cook, by voice.
You are a woman: use feminine verb forms for yourself (रही हूँ, बताती हूँ), never masculine (रहा हूँ).
Talk to the user with forms that need no gender, like डालो, करो, देखो, ले लो.
- 1-2 short sentences. The user is cooking, not reading.
- {language_rule}
- Warm and caring. Call the user "बेटा", written in Devanagari. {tease_rule}
- At most one audio tag, only where it fits: <sigh> for mistakes, <laugh> for jokes. Most replies need none.
- Tease only about cooking. Never about weight, looks, eating habits, money or anything personal.
- Cooking instructions beat jokes. Be supportive about mistakes, and use the listed fix first.
- Substitutes only from the listed ones. Otherwise say you have not tried it and suggest the safe option.
- Check "already added" before telling the user to add anything. Never add something twice.
- For salt, chilli, water or oil, repeat the recipe amount. If the user's amount differs, say no and give the recipe amount.
- Say amounts the way people talk: आधा चम्मच, एक कप, not 0.5 tsp.
- Never invent amounts or outcomes. If unsure, say so and suggest the safe option.
- Always call exactly one tool, with what you say in "reply".

{note}"""


def note(state):
    """The short note Amma ji reads before each turn. Built by code from the session state."""
    recipe = RECIPES[state["recipe_id"]]
    lang, n, total = state["language"], state["current_step"], len(recipe["steps"])
    # Hinglish shows English letters on screen, but Amma ji reads Devanagari so she replies in it
    read = "hi" if lang == "hi-en" else lang
    allergies = set(state["allergies"])
    def name(ingredient_id):
        # The spoken name first, so she says घी, and the id in brackets for the tools
        spoken = ingredient_name(ingredient_id, lang)
        return ingredient_id if spoken == ingredient_id else f"{spoken} [{ingredient_id}]"

    ingredients = []
    for i in recipe["ingredients"]:
        part = f"{name(i['id'])} {i['qty']:g} {i['unit']}"
        safe = [s for s in i.get("substitutes", []) if s not in allergies]
        if safe:
            part += f" (or {', '.join(name(s) for s in safe)})"
        ingredients.append(part)
    servings = state["servings"]
    if isinstance(servings, dict):  # from the recipe sheet: {"count": 2, "size": 1, "unit": "bowl"}
        servings = f"{servings.get('count') or 1:g} x {servings.get('size') or 1:g} {servings.get('unit') or 'serving'}"
    lines = [f"Recipe: {recipe['name']['en']} for {servings}. Now on step {n} of {total}.",
             "Ingredients: " + "; ".join(ingredients)]
    for k, label in ((n - 1, "Previous"), (n, "Current"), (n + 1, "Next")):
        if 1 <= k <= total:
            step = recipe["steps"][k - 1]
            safety = f" Safety: {in_language(step['safety'], 'en')}" if step.get("safety") else ""
            lines.append(f"{label} step {k}: {step_text(recipe, k, read)}{safety}")
    fixes = [f"{m['mistake']}: {m['fix'].get(read) or m['fix']['en']}" for m in recipe["common_mistakes"]]
    lines.append("Mistake fixes: " + " | ".join(fixes))
    lines.append("Already added: " + (", ".join(state["ingredients_added"]) or "nothing yet"))
    if state["substitutions"]:
        lines.append("Swapped (use these instead from now on): " + ", ".join(
            f"{name(x['from'])} -> {name(x['to'])}" for x in state["substitutions"]))
    lines.append("Steps done: " + (", ".join(map(str, state["completed_steps"])) or "none"))
    timers = live_timers(state)
    if timers:
        lines.append("Timers: " + ", ".join(
            f"{t['label']}: {t['seconds_left'] // 60} min {t['seconds_left'] % 60} s left" for t in timers))
    if allergies:
        lines.append("Allergies (never suggest these): " + ", ".join(sorted(allergies)))
    for h in state["history"]:
        lines.append(f"Earlier, user: {h['you']} / you: {h['amma']}")
    return "\n".join(lines)


def system_prompt(state):
    tease = "Lightly teasing, about cooking only." if state["teasing"] else "No teasing: plain, practical tone."
    return RULES.format(language_rule=LANGUAGE_RULES[state["language"]], tease_rule=tease, note=note(state))


# Every substitute any recipe lists, plus "none", so the model has to pick exactly one
SUBSTITUTES = sorted({s for r in RECIPES.values() for i in r["ingredients"] for s in i.get("substitutes", [])}) + ["none"]


def tool(name, when, **params):
    """One tool for Groq. `when` tells the model when to pick it; every tool also gets `reply`."""
    props = {**params, "reply": {"type": "string", "description": "What Amma ji says out loud"}}
    return {"type": "function", "function": {
        "name": name, "description": when,
        "parameters": {"type": "object", "properties": props, "required": list(props)}}}


TOOLS = [
    tool("next_step", "Ready for the next step. Reply reads it out."),
    tool("previous_step", "Asks about or wants the step before the current one."),
    tool("repeat_step", "Wants the current step again.", slow={"type": "boolean"}),
    tool("mark_added", "Says they added an ingredient.", ingredient={"type": "string", "description": "ingredient id"}),
    tool("substitute", "Is missing an ingredient.", ingredient={"type": "string", "description": "ingredient id"},
         to={"type": "string", "enum": SUBSTITUTES, "description": "the one listed substitute you suggest"}),
    tool("fix_mistake", "Made a mistake.", description={"type": "string"}),
    tool("adjust_spice", "Wants it more or less spicy.", direction={"type": "string", "enum": ["more", "less"]}),
    tool("start_timer", "Wants a timer.", minutes={"type": "number"},
         label={"type": "string", "description": "2-3 words the cook will recognise, like dal simmer"}),
    tool("check_timer", "Asks how much time is left."),
    tool("shorten_time", "Has less time than the recipe needs.", minutes_available={"type": "number"}),
    tool("answer_question", "Any other question about the recipe or step.", text={"type": "string"}),
]


def warm():
    """Open the Groq connection early (at session start), so the first question is not slowed by it."""
    key = os.getenv("GROQ_API_KEY")
    if key:
        try:
            HTTP.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=5)
        except requests.RequestException:
            pass


class BrainError(Exception):
    """Something went wrong talking to Groq. The message is safe to show the user."""


def ask(state, user_text):
    """One turn. Returns {tool, args, reply, ms, tokens}. Raises BrainError if Groq cannot answer."""
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise BrainError("The server has no GROQ_API_KEY set.")
    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system_prompt(state)},
                     {"role": "user", "content": normalise(user_text, state["language"])}],
        "tools": TOOLS,
        "tool_choice": "required",
        "temperature": 0.3,
        "max_completion_tokens": 1024,  # gpt-oss thinks first, and that thinking counts here
    }
    if MODEL.startswith("openai/gpt-oss"):
        body["reasoning_effort"] = "low"
    ms, retried = 0.0, False
    for _ in range(3):
        start = time.perf_counter()
        r = HTTP.post(URL, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=30)
        ms += (time.perf_counter() - start) * 1000
        if r.status_code == 400 and "tool_use_failed" in r.text and not retried:
            retried = True  # the model answered without a tool; ask once more
            continue
        if r.status_code == 429:
            wait = r.headers.get("retry-after", "a few")
            raise BrainError(f"Amma ji has had too many questions this minute. Try again in {wait} seconds.")
        break
    if r.status_code != 200:
        raise BrainError(f"Groq said {r.status_code}: {r.text[:200]}")
    data = r.json()
    calls = data["choices"][0]["message"].get("tool_calls") or []
    if not calls:
        raise BrainError("Amma ji did not pick an action. Try saying it another way.")
    fn = calls[0]["function"]
    try:
        args = json.loads(fn["arguments"] or "{}")
    except json.JSONDecodeError:
        raise BrainError("Amma ji's answer came back garbled. Try again.")
    reply = str(args.pop("reply", "")).strip()
    return {"tool": fn["name"], "args": args, "reply": reply, "ms": round(ms),
            "tokens": data.get("usage", {}).get("total_tokens"),
            "prompt_tokens": data.get("usage", {}).get("prompt_tokens")}


TIMER_WORDS = {
    "hi-en": ("बेटा, अभी कोई timer नहीं चल रहा।", "{label} में {left} बचे हैं", "{label} पूरा हो गया", "मिनट", "सेकंड"),
    "hi": ("बेटा, अभी कोई टाइमर नहीं चल रहा।", "{label} में {left} बचे हैं", "{label} पूरा हो गया", "मिनट", "सेकंड"),
    "pa": ("ਬੇਟਾ, ਹੁਣ ਕੋਈ ਟਾਈਮਰ ਨਹੀਂ ਚੱਲ ਰਿਹਾ।", "{label} ਵਿੱਚ {left} ਬਾਕੀ ਨੇ", "{label} ਪੂਰਾ ਹੋ ਗਿਆ", "ਮਿੰਟ", "ਸਕਿੰਟ"),
    "en": ("बेटा, no timer is running right now.", "{left} left on {label}", "{label} is done", "minutes", "seconds"),
}


def timer_reply(state):
    """The answer to "how much time is left", written by code from the real clock, never by the AI."""
    none, running, done, minutes, seconds = TIMER_WORDS[state["language"]]
    timers = live_timers(state)
    if not timers:
        return none
    parts = []
    for t in timers:
        s = t["seconds_left"]
        if s == 0:
            parts.append(done.format(label=t["label"]))
        else:
            left = f"{round(s / 60)} {minutes}" if s >= 90 else f"{s} {seconds}"
            parts.append(running.format(label=t["label"], left=left))
    end = "." if state["language"] == "en" else "।"
    return "बेटा, " + ", ".join(parts) + end


TAG = re.compile(r"<\s*/?\s*([a-z_]+)\s*>")
MIXED = re.compile(r"[\u0900-\u097F\u0A00-\u0A7F]+[A-Za-z]|[A-Za-z]+[\u0900-\u097F\u0A00-\u0A7F]")
MASCULINE = re.compile(r"(रहा|गया|सकता|करता|देता|लेता|बताता|लगाता|चाहता)\s*(हूँ|हूं)")


def warnings(reply):
    """Things worth a look while testing. Shown in dev mode, never to the cook."""
    found = []
    if len(TAG.findall(reply)) > 1:
        found.append("more than one audio tag")
    if MIXED.search(reply):
        found.append("a word mixes two scripts")
    if MASCULINE.search(reply):
        found.append("masculine verb form for Amma ji")
    return found


def screen_text(reply):
    """The reply without audio tags, for showing on screen."""
    return re.sub(r"\s{2,}", " ", TAG.sub("", reply)).strip()

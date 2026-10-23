"""Amma ji's brain for the Day 1 tests: a fake dal tadka session, the tools she can call, and one Groq call.

Every tool has a "reply" argument, so one Groq call gives us both the action (which tool) and
what Amma ji says out loud. One round trip instead of two keeps the delay low.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    sys.exit("GROQ_API_KEY missing. Copy backend/.env.example to backend/.env and fill it in.")

URL = "https://api.groq.com/openai/v1/chat/completions"
HTTP = requests.Session()  # keeps the connection to Groq open between calls

# A small hand-written recipe, in our own words. Real recipe files come in Days 3-5.
RECIPE = {
    "id": "dal_tadka",
    "name": {"en": "Dal Tadka", "hi": "दाल तड़का"},
    "servings": 2,
    "ingredients": [
        {"id": "toor_dal", "qty": 100, "unit": "g", "essential": True},
        {"id": "water", "qty": 2, "unit": "cup", "essential": True},
        {"id": "turmeric", "qty": 0.25, "unit": "tsp", "essential": False},
        {"id": "salt", "qty": 1, "unit": "tsp", "essential": True},
        {"id": "ghee", "qty": 1, "unit": "tbsp", "essential": False, "substitutes": ["oil", "butter"]},
        {"id": "cumin", "qty": 0.5, "unit": "tsp", "essential": False},
        {"id": "onion", "qty": 1, "unit": "medium", "essential": False},
        {"id": "garlic", "qty": 3, "unit": "clove", "essential": False},
        {"id": "tomato", "qty": 1, "unit": "medium", "essential": False},
        {"id": "red_chilli_powder", "qty": 0.5, "unit": "tsp", "essential": False},
        {"id": "garam_masala", "qty": 0.5, "unit": "tsp", "essential": False,
         "substitutes": ["kitchen_king", "skip"]},
    ],
    "steps": [
        {"n": 1, "text": "Wash the toor dal in water 2-3 times until the water looks clear."},
        {"n": 2, "text": "Put the dal in the pressure cooker with 2 cups water, turmeric and salt."},
        {"n": 3, "text": "Pressure cook on medium heat for 3 whistles, about 15 minutes.", "timer_min": 15,
         "safety": "Let the pressure release fully before opening the cooker."},
        {"n": 4, "text": "Open the cooker, mash the dal lightly and let it simmer for 5 minutes. "
                         "It should pour like thick soup.", "timer_min": 5},
        {"n": 5, "text": "For the tadka, heat ghee in a small pan, add cumin, and when it crackles add "
                         "chopped onion and garlic. Cook until golden."},
        {"n": 6, "text": "Add chopped tomato and red chilli powder. Cook until the tomato turns soft."},
        {"n": 7, "text": "Pour the tadka into the dal, add garam masala, simmer 2 minutes and serve."},
    ],
    "common_mistakes": [
        {"mistake": "too much water",
         "fix": {"en": "Keep the lid off and boil on high heat for 5 minutes, the extra water will dry up.",
                 "hi": "ढक्कन हटा के पाँच मिनट तेज़ आँच पे पकने दो, पानी सूख जाएगा।"}},
        {"mistake": "too thick",
         "fix": {"en": "Add half a cup of hot water, stir and boil for 2 minutes."}},
        {"mistake": "too salty",
         "fix": {"en": "Add half a cup of hot water and a squeeze of lemon. Do not add more salt."}},
        {"mistake": "too spicy",
         "fix": {"en": "Add a spoon of ghee and a little more boiled dal or water to soften the heat."}},
        {"mistake": "burnt tadka",
         "fix": {"en": "Throw the burnt tadka away and make a fresh one. Burnt cumin makes the dal bitter."}},
        {"mistake": "dal still hard",
         "fix": {"en": "Add a little water and pressure cook for 2 more whistles."}},
    ],
}

# The session state from brief section 7. Timers are worked out in code, never remembered by the model.
STATE = {
    "session_id": "day1-test",
    "language": "hi-en",
    "teasing": True,
    "recipe_id": "dal_tadka",
    "servings": 2,
    "current_step": 4,
    "completed_steps": [1, 2, 3],
    "ingredients_added": ["toor_dal", "water", "turmeric", "salt"],
    "substitutions": [],
    "quantity_changes": [],
    "allergies": ["peanut"],
    "timers": [{"label": "dal simmer", "minutes_left": 3}],
    "open_questions": [],
    "history_summary": "User washed and pressure cooked the dal. Now on step 4, simmering.",
}

LANGUAGE_RULES = {
    "hi": "Reply in Hindi written in Devanagari.",
    "hi-en": "Reply in Hinglish: Hindi words in Devanagari, common English words (cooker, timer, ok) may "
             "stay in English letters. Never write Hindi words in English letters.",
    "pa": "Reply in Punjabi written in Gurmukhi.",
    "en": "Reply in simple Indian English, in English letters. Only the word बेटा stays in Devanagari.",
}

SYSTEM_PROMPT = """You are Amma ji, a warm Indian mother helping the user cook, by voice.
You are a woman: always use feminine verb forms for yourself (रही हूँ, गई थी, बताती हूँ), never masculine (रहा हूँ).
Rules for every reply:
- 1-2 short sentences. The user is cooking, not reading.
- {language_rule}
- Warm and caring. Call the user "बेटा", written in Devanagari. {tease_rule}
- At most one audio tag per reply, only where it fits: <sigh> for mistakes, <laugh> for jokes. Most replies need none.
- Tease only about cooking. Never about weight, looks, eating habits, money or anything personal.
- Cooking instructions always beat jokes. Be supportive when the user makes a mistake.
- For mistakes, use the recipe's common_mistakes fix first.
- Substitutes only from the recipe's substitutes list. Otherwise say you have not tried it and suggest the safe option.
- Before telling the user to add something, check ingredients_added and completed_steps. If it is already in, say so and do not add it twice.
- For salt, chilli, water or oil quantities, repeat the recipe amount back. If the user's amount differs from the recipe, say no and give the recipe amount.
- Never invent outcomes. If unsure, say so and suggest the safe option.
- Always call exactly one tool. Put what you say out loud in its "reply" argument.

Recipe:
{recipe}

Session state:
{state}"""

REPLY = {"type": "string",
         "description": "What Amma ji says out loud: 1-2 short sentences in the session language, at most one audio tag."}


def tool(name, when, **params):
    """One tool for Groq. `when` tells the model when to pick it; every tool also gets `reply`."""
    props = {**params, "reply": REPLY}
    return {"type": "function", "function": {
        "name": name, "description": when,
        "parameters": {"type": "object", "properties": props, "required": list(props)}}}


TOOLS = [
    tool("next_step", "User is ready for the next step. Reply reads out the next step."),
    tool("previous_step", "User asks about or wants to go back to the step before the current one."),
    tool("repeat_step", "User wants the current step said again.",
         slow={"type": "boolean", "description": "True if the user asked to say it slowly"}),
    tool("mark_added", "User says they added an ingredient.",
         ingredient={"type": "string", "description": "Ingredient id from the recipe, e.g. turmeric"}),
    tool("substitute", "User does not have an ingredient and wants a replacement.",
         ingredient={"type": "string", "description": "Ingredient id the user is missing"}),
    tool("fix_mistake", "User made a mistake (too much water, too salty, burnt...).",
         description={"type": "string", "description": "Short description of the mistake"}),
    tool("adjust_spice", "User wants the dish more or less spicy.",
         direction={"type": "string", "enum": ["more", "less"]}),
    tool("start_timer", "User wants a timer.",
         minutes={"type": "number"}, label={"type": "string"}),
    tool("check_timer", "User asks how much time is left on a timer."),
    tool("shorten_time", "User has less time than the recipe needs.",
         minutes_available={"type": "number"}),
    tool("answer_question", "Any other question about the recipe or the current step.",
         text={"type": "string", "description": "The user's question"}),
]


def system_prompt(language="hi-en", teasing=True):
    state = {**STATE, "language": language, "teasing": teasing}
    tease = "Lightly teasing, about cooking only." if teasing else "No teasing: plain, practical tone."
    return SYSTEM_PROMPT.format(language_rule=LANGUAGE_RULES[language], tease_rule=tease,
                                recipe=json.dumps(RECIPE, ensure_ascii=False, separators=(",", ":")),
                                state=json.dumps(state, ensure_ascii=False, separators=(",", ":")))


def ask_groq(user_text, model, language="hi-en", teasing=True):
    """One Groq call. Returns a dict with tool, args, reply, ms, usage and rate limit headers.

    If Groq says "too many requests" (429), wait as long as it asks and try again (up to 3 times).
    The wait is reported separately and not counted in ms.
    """
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt(language, teasing)},
                     {"role": "user", "content": user_text}],
        "tools": TOOLS,
        "tool_choice": "required",
        "temperature": 0.3,
        # gpt-oss models think before answering, and the thinking counts toward this limit.
        "max_completion_tokens": 1024,
    }
    if model.startswith("openai/gpt-oss"):
        body["reasoning_effort"] = "low"  # docs: low, medium (default) or high. Low is fastest.
    waited = 0.0
    for _ in range(4):
        start = time.perf_counter()
        r = HTTP.post(URL, headers={"Authorization": f"Bearer {API_KEY}"}, json=body, timeout=60)
        ms = (time.perf_counter() - start) * 1000
        if r.status_code != 429:
            break
        pause = float(r.headers.get("retry-after", 10))
        print(f"    (rate limited, waiting {pause:.0f} s)")
        time.sleep(pause)
        waited += pause
    limits = {k: v for k, v in r.headers.items() if k.lower().startswith("x-ratelimit")}
    if r.status_code != 200:
        return {"error": f"{r.status_code}: {r.text[:300]}", "ms": ms, "waited_s": waited, "limits": limits}
    data = r.json()
    msg = data["choices"][0]["message"]
    calls = msg.get("tool_calls") or []
    if not calls:
        return {"error": "no tool call", "reply": msg.get("content") or "", "ms": ms,
                "usage": data.get("usage", {}), "limits": limits}
    fn = calls[0]["function"]
    try:
        args = json.loads(fn["arguments"] or "{}")
    except json.JSONDecodeError:
        return {"error": f"bad JSON arguments: {fn['arguments'][:200]}", "tool": fn["name"], "ms": ms,
                "usage": data.get("usage", {}), "limits": limits}
    return {"tool": fn["name"], "args": args, "reply": args.pop("reply", ""), "extra_calls": len(calls) - 1,
            "ms": ms, "waited_s": waited, "usage": data.get("usage", {}), "limits": limits}


TAG = re.compile(r"<\s*/?\s*([a-z_]+)\s*>")
KNOWN_TAGS = {"sigh", "laugh", "pauses", "slow", "whispers", "excited", "giggle"}


def check_reply(reply, language):
    """Simple rule checks on a reply. Returns a list of problems (empty list means it passed)."""
    problems = []
    if not reply.strip():
        return ["empty reply"]
    tags = TAG.findall(reply)
    if len(tags) > 1:
        problems.append(f"{len(tags)} audio tags")
    problems += [f"unknown tag <{t}>" for t in tags if t not in KNOWN_TAGS]
    text = TAG.sub("", reply)
    sentences = [s for s in re.split(r"[.?!।]+", text) if s.strip()]
    if len(sentences) > 2:
        problems.append(f"{len(sentences)} sentences")
    devanagari = len(re.findall(r"[ऀ-ॿ]", text))
    gurmukhi = len(re.findall(r"[਀-੿]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if language in ("hi", "hi-en") and devanagari < latin:
        problems.append("mostly English letters (romanized Hindi?)")
    if language == "pa" and gurmukhi < latin + devanagari:
        problems.append("not Gurmukhi")
    if language == "en" and latin < devanagari + gurmukhi:
        problems.append("not English")
    return problems

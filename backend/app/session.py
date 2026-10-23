"""One cooking session: the state from brief section 7, and the code that carries out each tool.

The AI only picks a tool and writes what Amma ji says. This file does the actual work: steps,
added ingredients and timers change here, in code, so they stay right even if the AI slips.
"""
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

RECIPES = {
    p.stem: json.loads(p.read_text(encoding="utf-8"))
    for p in sorted((Path(__file__).parent / "recipes").glob("*.json"))
}
# Ingredient names in each language (and common spellings, for matching what people say later)
INGREDIENTS = {
    i["id"]: i for i in json.loads((Path(__file__).parent / "data" / "ingredients.json").read_text(encoding="utf-8"))
}
# Kept in memory for the MVP: restarting the server forgets every session.
SESSIONS = {}
LANGUAGES = {"hi-en", "hi", "pa", "en"}


def now():
    return datetime.now(timezone.utc)


def new_session(recipe_id, language="hi-en", teasing=True, allergies=()):
    if recipe_id not in RECIPES:
        raise KeyError(recipe_id)
    if language not in LANGUAGES:
        raise ValueError(language)
    state = {
        "session_id": uuid.uuid4().hex[:12],
        "language": language,
        "teasing": teasing,
        "recipe_id": recipe_id,
        "servings": RECIPES[recipe_id]["servings"],
        "current_step": 1,
        "completed_steps": [],
        "ingredients_added": [],
        "substitutions": [],
        "quantity_changes": [],
        "allergies": [a.strip().lower() for a in allergies if a.strip()],
        "timers": [],
        "open_questions": [],
        "history": [],  # last 3 exchanges only, never the full transcript
    }
    SESSIONS[state["session_id"]] = state
    return state


def ingredient_name(ingredient_id, language):
    """घी for Hindi and Hinglish, ਘਿਓ for Punjabi, ghee for English. Falls back to the id."""
    names = INGREDIENTS.get(ingredient_id, {}).get("names", {})
    return names.get("hi" if language == "hi-en" else language) or names.get("en") or ingredient_id


# Every known spelling, longest first, so "desi ghee" wins over "ghee"
SPELLINGS = sorted(((sp, i["id"]) for i in INGREDIENTS.values() for sp in i["spellings"]),
                   key=lambda pair: -len(pair[0]))


def normalise(text, language):
    """Swap ingredient words written in English letters for their proper name: ghee becomes घी.

    Hindi and Punjabi replies come out cleaner when the question already uses the right script.
    """
    if language == "en":
        return text
    for spelling, ingredient_id in SPELLINGS:
        name = ingredient_name(ingredient_id, language)
        text = re.sub(rf"(?<![\w]){re.escape(spelling)}(?![\w])", name, text, flags=re.IGNORECASE)
    return text


def step_text(recipe, n, language):
    text = recipe["steps"][n - 1]["text"]
    return text.get(language) or text["en"]


def live_timers(state):
    """Timers with seconds left, worked out from the clock. Drops ones that ended over 5 minutes ago."""
    out = []
    for t in state["timers"]:
        left = (datetime.fromisoformat(t["ends_at"]) - now()).total_seconds()
        if left > -300:
            out.append({**t, "seconds_left": max(0, round(left))})
    return out


def public(state):
    """What the app gets back: the state, live timers, and the current step ready to show."""
    recipe = RECIPES[state["recipe_id"]]
    n = state["current_step"]
    step = recipe["steps"][n - 1]
    return {
        **{k: v for k, v in state.items() if k != "timers"},
        "timers": live_timers(state),
        "total_steps": len(recipe["steps"]),
        "recipe_name": recipe["name"].get(state["language"]) or recipe["name"]["en"],
        "step": {"n": n, "text": step_text(recipe, n, state["language"]),
                 # what Timbre reads aloud: Devanagari for Hinglish, since romanized Hindi is misread
                 "speak": step_text(recipe, n, "hi" if state["language"] == "hi-en" else state["language"]),
                 "safety": step.get("safety"), "timer_min": step.get("timer_min")},
    }


def go_to_step(state, n):
    """Move to step n (kept between the first and last step).

    Moving forward marks the steps before n as done, and their ingredients as added.
    """
    recipe = RECIPES[state["recipe_id"]]
    n = max(1, min(len(recipe["steps"]), n))
    if n > state["current_step"]:
        state["completed_steps"] = sorted(set(state["completed_steps"]) | set(range(1, n)))
        for step in recipe["steps"][: n - 1]:
            for ingredient in step["uses"]:
                if ingredient not in state["ingredients_added"]:
                    state["ingredients_added"].append(ingredient)
    state["current_step"] = n


def apply_tool(state, tool, args):
    """Carry out what the AI decided. Returns extra instructions for the app, like a slower voice."""
    recipe = RECIPES[state["recipe_id"]]
    ingredient_ids = {i["id"] for i in recipe["ingredients"]}
    effect = {}
    if tool == "next_step":
        go_to_step(state, state["current_step"] + 1)
    elif tool == "previous_step":
        go_to_step(state, state["current_step"] - 1)
    elif tool == "repeat_step" and args.get("slow"):
        effect["tts_speed"] = 0.85
    elif tool == "mark_added":
        ingredient = str(args.get("ingredient", "")).strip().lower()
        if ingredient in ingredient_ids and ingredient not in state["ingredients_added"]:
            state["ingredients_added"].append(ingredient)
    elif tool == "substitute":
        # Only swaps the recipe lists, and never one the user is allergic to
        missing = str(args.get("ingredient", "")).strip().lower()
        choice = str(args.get("to", "")).strip().lower()
        listed = next((i.get("substitutes", []) for i in recipe["ingredients"] if i["id"] == missing), [])
        if choice in listed and choice not in state["allergies"]:
            state["substitutions"] = [x for x in state["substitutions"] if x["from"] != missing]
            state["substitutions"].append({"from": missing, "to": choice})
    elif tool == "adjust_spice" and args.get("direction") in ("more", "less"):
        state["quantity_changes"].append({"spice": args["direction"], "at_step": state["current_step"]})
    elif tool == "start_timer":
        try:
            minutes = float(args.get("minutes", 0))
        except (TypeError, ValueError):
            minutes = 0
        if 0 < minutes <= 180:
            label = str(args.get("label") or "timer").replace("_", " ").strip()[:40] or "timer"
            ends = now() + timedelta(minutes=minutes)
            state["timers"].append({"label": label, "minutes": minutes, "ends_at": ends.isoformat()})
            effect["timer_started"] = {"label": label, "minutes": minutes}
    return effect


def remember_turn(state, said, reply):
    state["history"] = (state["history"] + [{"you": said[:200], "amma": reply[:200]}])[-3:]

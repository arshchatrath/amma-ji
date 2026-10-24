"""Flow F: the end of a cooking session. Everything here is built in code, so it costs no AI calls.

The summary says what was made, what was changed on the way, how long it took and the nutrition
estimate. "How was it?" gets a fixed line from Amma ji, and tips from the dish's common mistakes
if it did not turn out well.
"""
import logging
from datetime import datetime

from .pantry import display_name
from .session import RECIPES, go_to_step, now

log = logging.getLogger("amma.feedback")

# Each line comes twice: what the screen shows, and what Timbre reads (Devanagari for Hinglish)
CLOSING = {
    "hi-en": ("Shabaash beta! {dish} ban gaya. Garam garam khao.", "शाबाश बेटा! {dish} बन गया। गरम-गरम खाओ।"),
    "hi": ("शाबाश बेटा! {dish} बन गया। गरम-गरम खाओ।", None),
    "pa": ("ਸ਼ਾਬਾਸ਼ ਬੇਟਾ! {dish} ਬਣ ਗਿਆ। ਗਰਮ-ਗਰਮ ਖਾਓ।", None),
    "en": ("Well done, beta! The {dish} is ready. Eat it while it's hot.", "Well done, बेटा! The {dish} is ready. Eat it while it's hot."),
}

FEEDBACK = {
    "loved": {
        "hi-en": ("Mujhe pata tha! Agli baar kuch naya banayenge.", "मुझे पता था! अगली बार कुछ नया बनाएँगे।"),
        "hi": ("मुझे पता था! अगली बार कुछ नया बनाएँगे।", None),
        "pa": ("ਮੈਨੂੰ ਪਤਾ ਸੀ! ਅਗਲੀ ਵਾਰ ਕੁਝ ਨਵਾਂ ਬਣਾਵਾਂਗੇ।", None),
        "en": ("I knew it! Next time we'll make something new.", None),
    },
    "okay": {
        "hi-en": ("Theek bana, yeh bhi kam nahi hai. Agli baar aur achha banega.", "ठीक बना, यह भी कम नहीं है। अगली बार और अच्छा बनेगा।"),
        "hi": ("ठीक बना, यह भी कम नहीं है। अगली बार और अच्छा बनेगा।", None),
        "pa": ("ਠੀਕ ਬਣਿਆ, ਇਹ ਵੀ ਘੱਟ ਨਹੀਂ। ਅਗਲੀ ਵਾਰ ਹੋਰ ਵਧੀਆ ਬਣੇਗਾ।", None),
        "en": ("Good enough, and that's not nothing. It will be even better next time.", None),
    },
    "bad": {
        "hi-en": ("Koi baat nahi beta, pehli baar sabse hota hai. Yeh dekh lo, agli baar kaam aayega.",
                  "कोई बात नहीं बेटा, पहली बार सबसे होता है। यह देख लो, अगली बार काम आएगा।"),
        "hi": ("कोई बात नहीं बेटा, पहली बार सबसे होता है। यह देख लो, अगली बार काम आएगा।", None),
        "pa": ("ਕੋਈ ਗੱਲ ਨਹੀਂ ਬੇਟਾ, ਪਹਿਲੀ ਵਾਰ ਸਭ ਨਾਲ ਹੁੰਦਾ ਹੈ। ਇਹ ਵੇਖ ਲਓ, ਅਗਲੀ ਵਾਰ ਕੰਮ ਆਵੇਗਾ।", None),
        "en": ("Never mind, beta, it happens to everyone the first time. Have a look at these for next time.",
               "Never mind, बेटा, it happens to everyone the first time. Have a look at these for next time."),
    },
}

SWAPPED = {"hi-en": "{to} use kiya, {from_} ki jagah", "hi": "{from_} की जगह {to}", "pa": "{from_} ਦੀ ਥਾਂ {to}",
           "en": "Used {to} instead of {from_}"}
SPICE = {
    "more": {"hi-en": "Mirch badhaayi", "hi": "मिर्च बढ़ाई", "pa": "ਮਿਰਚ ਵਧਾਈ", "en": "Made it spicier"},
    "less": {"hi-en": "Mirch kam ki", "hi": "मिर्च कम की", "pa": "ਮਿਰਚ ਘੱਟ ਕੀਤੀ", "en": "Made it less spicy"},
}


def line(pair, shown_values=None, spoken_values=None):
    shown, spoken = pair
    return {"text": shown.format(**(shown_values or {})),
            "speak": (spoken or shown).format(**(spoken_values or shown_values or {}))}


def minutes_taken(state):
    end = datetime.fromisoformat(state.get("finished_at") or now().isoformat())
    return max(1, round((end - datetime.fromisoformat(state["started_at"])).total_seconds() / 60))


def summary(state):
    """Mark the dish as done and say what happened, in the cook's language."""
    recipe = RECIPES[state["recipe_id"]]
    lang = state["language"]
    go_to_step(state, len(recipe["steps"]))
    state["completed_steps"] = list(range(1, len(recipe["steps"]) + 1))
    state["finished_at"] = state.get("finished_at") or now().isoformat()
    dish = recipe["name"].get(lang) or recipe["name"]["en"]
    spoken_dish = recipe["name"].get("hi" if lang == "hi-en" else lang) or dish
    changes = [SWAPPED[lang].format(from_=display_name(x["from"], lang), to=display_name(x["to"], lang))
               for x in state["substitutions"]]
    spice = [c["spice"] for c in state["quantity_changes"] if "spice" in c]
    if spice:
        changes.append(SPICE[spice[-1]][lang])
    n = recipe.get("nutrition_per_serving") or {}
    return {
        "dish_id": recipe.get("id", state["recipe_id"]),
        "recipe_name": dish,
        "language": lang,
        "minutes": minutes_taken(state),
        "changes": changes,
        "nutrition": n if n.get("kcal") else None,
        "closing": line(CLOSING[lang], {"dish": dish}, {"dish": spoken_dish}),
        "feedback": state.get("feedback"),
    }


def feedback(state, rating):
    """Remember how it went (in the server log, nothing personal) and answer kindly."""
    recipe = RECIPES[state["recipe_id"]]
    lang = state["language"]
    state["feedback"] = rating
    log.info("feedback dish=%s language=%s rating=%s minutes=%s swaps=%d",
             state["recipe_id"], lang, rating, minutes_taken(state), len(state["substitutions"]))
    tips = []
    if rating == "bad":
        # The fixes are written in English and Hindi; Hinglish and Punjabi screens show the English ones
        tips = [{"problem": m["mistake"], "fix": m["fix"].get("hi" if lang == "hi" else "en") or m["fix"]["en"]}
                for m in recipe["common_mistakes"][:3]]
    return {"reply": line(FEEDBACK[rating][lang]), "tips": tips}

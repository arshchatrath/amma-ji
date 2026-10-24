"""Flow B and C: what the cook has, and which dishes fit. Plain code, no AI, so it costs no Groq calls.

hear()    "do aloo, paneer, pyaaz hai, 20 minute mein" -> {have: [potato, paneer, onion], minutes: 20}
          Works for English letters, Devanagari and Gurmukhi, any common spelling.
suggest() ranks the cookable dishes: must-haves first, then how many of your things a dish uses,
          then fewest missing extras, then time. Allergies and diet are filters, never suggestions.
"""
import re

from .session import INGREDIENTS, RECIPES, ingredient_name, in_language

SEP = r"\s,.;:!?।|/()\-"
# "paneer nahi hai": these come after the word they cancel
NEGATIONS = {"nahi", "nahin", "nhi", "nai", "khatam", "khattam", "finished", "नहीं", "नही", "ख़त्म", "खत्म",
             "ਨਹੀਂ", "ਨਹੀ", "ਖ਼ਤਮ", "ਖਤਮ"}
# "no butter", "bina pyaaz": these come before it
BEFORE_NEGATIONS = {"bina", "without", "no", "not", "बिना", "ਬਿਨਾਂ", "ਬਿਨਾ"}
NUMBERS = {
    "paanch": 5, "panch": 5, "five": 5, "पाँच": 5, "पांच": 5, "ਪੰਜ": 5,
    "das": 10, "dus": 10, "ten": 10, "दस": 10, "ਦਸ": 10,
    "pandrah": 15, "pandra": 15, "fifteen": 15, "पंद्रह": 15, "ਪੰਦਰਾਂ": 15,
    "bees": 20, "bis": 20, "twenty": 20, "बीस": 20, "ਵੀਹ": 20,
    "pachchees": 25, "pachees": 25, "पच्चीस": 25, "ਪੱਚੀ": 25,
    "tees": 30, "thirty": 30, "तीस": 30, "ਤੀਹ": 30,
    "chaalees": 40, "chalees": 40, "forty": 40, "चालीस": 40, "ਚਾਲੀ": 40,
    "pachaas": 50, "pachas": 50, "fifty": 50, "पचास": 50, "ਪੰਜਾਹ": 50,
}
MINUTE_WORDS = r"(?:min|mins|minute|minutes|minat|मिनट|ਮਿੰਟ)"
QUICK_WORDS = {"jaldi", "quick", "quickly", "fast", "जल्दी", "ਛੇਤੀ", "ਜਲਦੀ"}
HALF_HOUR = r"(aadha|adha|half an?|आधा|ਅੱਧਾ)\s*(ghanta|ghante|hour|घंटा|घंटे|ਘੰਟਾ|ਘੰਟੇ)"
ONE_HOUR = r"(ek|one|an|1|एक|ਇੱਕ)\s*(ghanta|hour|घंटा|ਘੰਟਾ)"
VEG_WORDS = r"\b(veg|vegetarian|shakahari|eggless)\b|शाकाहारी|ਸ਼ਾਕਾਹਾਰੀ|bina (anda|ande)|no egg|बिना अंड"
SWEET_WORDS = r"\b(meetha|mitha|sweet|dessert)\b|मीठा|ਮਿੱਠਾ"
DRINK_WORDS = r"\b(drink|peene|peena|sharbat)\b|पीने|ਪੀਣ"
MEAL_KINDS = ["main", "bread", "snack", "soup"]


def fold(text):
    """Lower-case, and treat spelling variants of the same letter alike (nukta dots, chandrabindu)."""
    text = text.lower()
    for a, b in (("़", ""), ("਼", ""), ("ँ", "ं"), ("ਂ", "ੰ")):
        text = text.replace(a, b)
    return text


def _phrases():
    """Every way to say every ingredient, longest first so 'desi ghee' wins over 'ghee'."""
    pairs = set()
    for ing in INGREDIENTS.values():
        if "additive" in ing.get("labels", []):
            continue
        words = set(ing["spellings"]) | {ing["names"].get(k, "") for k in ("en", "hi", "pa")}
        for w in words - {""}:
            w = fold(w)
            pairs.add((w, ing["id"]))
            if re.fullmatch(r"[a-z ]+", w):  # English letters: also tomatoes, onions, chillies
                pairs.update({(w + "s", ing["id"]), (w + "es", ing["id"])})
                if w.endswith("y"):
                    pairs.add((w[:-1] + "ies", ing["id"]))
    return sorted(pairs, key=lambda p: -len(p[0]))


PHRASES = _phrases()


def hear(text):
    """What the cook said, as ingredient ids they have (and do not have), time limit and diet."""
    folded = f" {fold(text)} "
    found = []  # (start, end, id)
    taken = [False] * len(folded)
    for phrase, ing_id in PHRASES:
        for m in re.finditer(rf"(?<![^{SEP}]){re.escape(phrase)}(?![^{SEP}])", folded):
            if not any(taken[m.start():m.end()]):
                found.append((m.start(), m.end(), ing_id))
                for k in range(m.start(), m.end()):
                    taken[k] = True
    found.sort()
    have, not_have = [], []
    for n, (start, end, ing_id) in enumerate(found):
        stop = found[n + 1][0] if n + 1 < len(found) else len(folded)
        after = re.split(r"[,.;।]", folded[end:stop])[0].split()[:3]  # stop at the next comma
        before = folded[:start].split()[-1:]
        negated = any(w.strip("!?") in NEGATIONS for w in after) or any(w in BEFORE_NEGATIONS for w in before)
        target = not_have if negated else have
        if ing_id not in target:
            target.append(ing_id)
    have = [i for i in have if i not in not_have]

    minutes = None
    m = re.search(rf"(\d+)\s*{MINUTE_WORDS}", folded)
    if m:
        minutes = int(m.group(1))
    else:
        m = re.search(rf"(\S+)\s*{MINUTE_WORDS}", folded)
        if m and m.group(1) in NUMBERS:
            minutes = NUMBERS[m.group(1)]
        elif re.search(HALF_HOUR, folded):
            minutes = 30
        elif re.search(ONE_HOUR, folded):
            minutes = 60
        elif set(folded.split()) & QUICK_WORDS:
            minutes = 20
    kinds = ["dessert"] if re.search(SWEET_WORDS, folded) else ["drink"] if re.search(DRINK_WORDS, folded) else None
    diet = "veg" if re.search(VEG_WORDS, folded) and "non veg" not in folded and "non-veg" not in folded else None
    return {"have": have, "not_have": not_have, "minutes": minutes, "diet": diet, "kinds": kinds}


def _labels(ing_id):
    return set(INGREDIENTS.get(ing_id, {}).get("labels", []))


def display_name(ing_id, language):
    """aloo for Hinglish screens, आलू for Hindi, ਆਲੂ for Punjabi, potato for English."""
    if language == "hi-en":
        spellings = INGREDIENTS.get(ing_id, {}).get("spellings", [])
        return spellings[0] if spellings else ing_id.replace("_", " ")
    return ingredient_name(ing_id, language)


def _diet(recipe):
    diet = recipe.get("diet", "veg")
    return ("veg" if "vegetarian" in diet else "non_veg") if isinstance(diet, list) else diet


def _minutes(recipe):
    return recipe.get("total_min") or (recipe.get("prep_min") or 0) + (recipe.get("cook_min") or 0) or None


def check(recipe, have, not_have=(), allergies=()):
    """How one dish fits: what is missing, what can be swapped, which of the cook's things it uses."""
    have, not_have, allergies = set(have), set(not_have), {a.lower() for a in allergies}
    has_fat = bool(have & {"oil", "ghee", "butter"}) or "oil" not in not_have
    missing_essential, missing_optional, swaps, uses, seen = [], [], [], [], set()
    for ing in recipe["ingredients"]:
        ing_id = ing["id"]
        if ing_id in seen:
            continue
        seen.add(ing_id)
        labels = _labels(ing_id)
        if ing_id in allergies or labels & allergies:
            return None
        if "additive" in labels:
            continue
        if ing_id in have:
            if not labels & {"pantry"}:
                uses.append(ing_id)
            continue
        if "pantry" in labels and ing_id not in not_have:
            continue
        if "fat" in labels and has_fat:
            continue
        swap = next((s for s in ing.get("substitutes", []) if s in have or s == "skip"), None)
        if swap:
            swaps.append({"from": ing_id, "to": swap})
            continue
        if "garnish" in labels:
            continue
        (missing_essential if ing.get("essential") else missing_optional).append(ing_id)
    if set(recipe.get("allergens", [])) & allergies:
        return None
    return {"missing_essential": missing_essential, "missing_optional": missing_optional, "swaps": swaps,
            "uses": uses}


def label_for(fit):
    if fit["missing_essential"]:
        return "missing_essential"
    return {0: "can_make_now", 1: "needs_one_optional"}.get(len(fit["missing_optional"]), "needs_optional")


# Worded so they work for any ingredient (no he/she agreement to get wrong)
WHY = {
    "en": ("Uses your {uses}.", "Ready in about {min} minutes.", "You need {missing}.", "Skip or add {missing}."),
    "hi-en": ("Tumhare saamaan mein se: {uses}.", "Lagbhag {min} minute mein ban jayega.", "{missing} chahiye.",
              "{missing} ho to daalo, nahi to chhod do."),
    "hi": ("तुम्हारे सामान में से: {uses}।", "लगभग {min} मिनट में बन जाएगा।", "{missing} चाहिए।",
           "{missing} हो तो डालो, नहीं तो छोड़ दो।"),
    "pa": ("ਤੁਹਾਡੇ ਸਮਾਨ ਵਿੱਚੋਂ: {uses}।", "ਲਗਭਗ {min} ਮਿੰਟ ਵਿੱਚ ਬਣ ਜਾਵੇਗਾ।", "{missing} ਦੀ ਲੋੜ ਹੈ।",
           "{missing} ਹੋਵੇ ਤਾਂ ਪਾਓ, ਨਹੀਂ ਤਾਂ ਛੱਡ ਦਿਓ।"),
}
AND = {"en": "and", "hi-en": "aur", "hi": "और", "pa": "ਅਤੇ"}


def _join(ids, language):
    names = [display_name(i, language) for i in ids]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + f" {AND[language]} {names[-1]}"


def why(fit, minutes, language):
    """One short line on why this dish fits, built from the ranking result (no AI)."""
    uses_t, time_t, need_t, skip_t = WHY[language]
    parts = []
    if fit["uses"]:
        parts.append(uses_t.format(uses=_join(fit["uses"][:3], language)))
    if fit["missing_essential"]:
        parts.append(need_t.format(missing=_join(fit["missing_essential"][:2], language)))
    elif fit["missing_optional"]:
        parts.append(skip_t.format(missing=_join(fit["missing_optional"][:2], language)))
    if minutes:
        parts.append(time_t.format(min=minutes))
    return " ".join(p[:1].upper() + p[1:] for p in parts)


def suggest(have, not_have=(), minutes=None, diet=None, allergies=(), kinds=None, language="hi-en", limit=3):
    """The best dishes for what the cook has, ranked in code, each with an honest label."""
    kinds = kinds or MEAL_KINDS
    ranked = []
    for recipe in RECIPES.values():
        kind = recipe.get("kind", "main")
        if kind not in kinds:
            continue
        dish_diet = _diet(recipe)
        if diet == "veg" and dish_diet != "veg":
            continue
        fit = check(recipe, have, not_have, allergies)
        if fit is None or (have and not fit["uses"]):
            continue
        total = _minutes(recipe)
        too_long = bool(minutes and total and total > minutes)
        ranked.append(((len(fit["missing_essential"]), -len(fit["uses"]), len(fit["missing_optional"]),
                        too_long, total or 999), recipe, fit, total, too_long))
    ranked.sort(key=lambda r: r[0])
    out = []
    for _, recipe, fit, total, too_long in ranked[:limit]:
        n = recipe.get("nutrition_per_serving") or {}
        out.append({
            "id": recipe.get("id", "dal_tadka"),
            "name": in_language(recipe["name"], language),
            "kind": recipe.get("kind", "main"),
            "diet": _diet(recipe),
            "label": label_for(fit),
            "why": why(fit, total, language),
            "minutes": total,
            "longer_than_you_have": too_long,
            "uses": [display_name(i, language) for i in fit["uses"]],
            "missing_essential": [display_name(i, language) for i in fit["missing_essential"]],
            "missing_optional": [display_name(i, language) for i in fit["missing_optional"]],
            "swaps": [{"from": display_name(s["from"], language), "to": display_name(s["to"], language)
                       if s["to"] != "skip" else "skip"} for s in fit["swaps"]],
            "kcal": n.get("kcal"),
            "nutrition_per": n.get("per"),
        })
    return out


def card(recipe, language):
    """Flow D: everything the recipe card shows, in the cook's language."""
    n = recipe.get("nutrition_per_serving")
    seen, ingredients = set(), []
    for ing in recipe["ingredients"]:
        if ing["id"] in seen or "additive" in _labels(ing["id"]):
            continue
        seen.add(ing["id"])
        ingredients.append({"id": ing["id"], "name": display_name(ing["id"], language), "qty": ing.get("qty"),
                            "unit": ing.get("unit"), "essential": bool(ing.get("essential")),
                            "substitutes": [display_name(x, language) if x != "skip" else "skip"
                                            for x in ing.get("substitutes", [])]})
    return {
        "id": recipe.get("id", "dal_tadka"),
        "name": in_language(recipe["name"], language),
        "kind": recipe.get("kind", "main"),
        "diet": _diet(recipe),
        "allergens": recipe.get("allergens", []),
        "servings": recipe.get("servings"),
        "minutes": _minutes(recipe),
        "ingredients": ingredients,
        "steps": [in_language(st["text"], language) for st in recipe["steps"]],
        "nutrition": n if n and n.get("kcal") else None,
        "source_note": recipe.get("source_note"),
        "source_link": recipe.get("source_link"),
    }


def ingredient_list(language):
    """Every ingredient people might have, for adding a chip by hand."""
    return sorted(({"id": i["id"], "name": display_name(i["id"], language)} for i in INGREDIENTS.values()
                   if not {"additive", "pantry"} & set(i.get("labels", []))), key=lambda x: x["name"])


# Flow C by voice: "doosra wala", "number 2", "aloo paratha wala". Positions people say, in each language.
ORDINALS = {
    1: {"pehla", "pehle", "pehli", "pahla", "pahle", "first", "ek", "1", "पहला", "पहले", "पहली", "एक", "ਪਹਿਲਾ", "ਪਹਿਲੀ", "ਇੱਕ"},
    2: {"doosra", "dusra", "doosri", "dusri", "second", "two", "2", "दूसरा", "दूसरी", "दूसरे", "ਦੂਜਾ", "ਦੂਜੀ", "ਦੋ"},
    3: {"teesra", "tisra", "teesri", "tisri", "third", "teen", "three", "3", "तीसरा", "तीसरी", "तीन", "ਤੀਜਾ", "ਤੀਜੀ", "ਤਿੰਨ"},
    4: {"chautha", "chauthi", "fourth", "char", "chaar", "four", "4", "चौथा", "चौथी", "चार", "ਚੌਥਾ", "ਚੌਥੀ", "ਚਾਰ"},
    5: {"paanchva", "panchva", "paanchvi", "fifth", "paanch", "five", "5", "पाँचवाँ", "पांचवा", "पाँचवीं", "पाँच", "पांच",
        "ਪੰਜਵਾਂ", "ਪੰਜਵੀਂ", "ਪੰਜ"},
    6: {"6", "six", "sixth", "chhe", "छह", "छठा", "ਛੇ"}, 7: {"7", "seven", "seventh", "saat", "सात", "ਸੱਤ"},
    8: {"8", "eight", "eighth", "aath", "आठ", "ਅੱਠ"}, 9: {"9", "nine", "ninth", "nau", "नौ", "ਨੌਂ"},
    10: {"10", "ten", "tenth", "das", "दस", "ਦਸ"},
}
LAST = {"last", "aakhri", "akhri", "aakhiri", "आखिरी", "आख़िरी", "अंतिम", "ਆਖਰੀ", "ਆਖ਼ਰੀ"}
# "do" (two) is left out of the numbers: in Hinglish it is far more often "give". "one" is left out
# too, so "the second one" means the second.
NOT_A_NAME = {"wala", "wali", "wale", "number", "banao", "bana", "banate", "karo", "dish", "recipe", "the", "one", "please",
              "वाला", "वाली", "वाले", "नंबर", "बनाओ", "बना", "ਵਾਲਾ", "ਵਾਲੀ", "ਨੰਬਰ", "ਬਣਾਓ", "amma", "ji", "अम्मा", "जी"}


MARKS = re.compile("[\u0901\u0902\u093c\u0a01\u0a02\u0a3c\u0a70\u0a71]")  # nasal marks, nukta, addak


# The same marks dropped from the position words, so they compare with what was said
ORDINALS = {n: {MARKS.sub("", w) for w in words} for n, words in ORDINALS.items()}
LAST = {MARKS.sub("", w) for w in LAST}


def _words(text):
    """Words to compare, with nasal marks and nukta dropped: परांठा and पराठा are the same word."""
    text = MARKS.sub("", re.sub(r"[^\w\s\u0900-\u097F\u0A00-\u0A7F]|[।॥]", " ", text.lower()))
    return {w for w in re.split(r"[\s/()]+", text) if w and w not in NOT_A_NAME}


def pick(text, options):
    """Which of the shown dishes the cook means. A dish's name wins over a position."""
    said = _words(text)
    shown = [(n, d, RECIPES[d]) for n, d in enumerate(options) if d in RECIPES]
    names = {d: {w for name in (r["name"].values() if isinstance(r["name"], dict) else [r["name"]])
                 for w in _words(name) if len(w) > 2} for _, d, r in shown}
    # Only words that tell the shown dishes apart count: "paratha" says nothing when all three are parathas
    common = set.intersection(*names.values()) if len(names) > 1 else set()
    scores = sorted(((len((said & names[d]) - common), -n, d) for n, d, _ in shown), reverse=True)
    if scores and scores[0][0] and (len(scores) == 1 or scores[0][0] > scores[1][0]):
        return {"id": scores[0][2], "how": "name"}
    if said & LAST and options:
        return {"id": options[-1], "how": "number"}
    for n, words_for_n in ORDINALS.items():
        if said & words_for_n and n <= len(options):
            return {"id": options[n - 1], "how": "number"}
    return {"id": None, "how": None}

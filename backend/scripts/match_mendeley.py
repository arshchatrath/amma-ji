"""Finds which INDB dishes also appear in the Mendeley "6000+ Indian Food Recipes Dataset".

Mendeley dataset: Kanishka Jain (2020), https://data.mendeley.com/datasets/xsphgmmh7b/1, CC BY 4.0.
It was built from archanaskitchen.com, so its ingredient and step TEXT belongs to that site and is
never stored here. Only plain facts are kept for matched dishes: prep, cook and total minutes,
course, cuisine, diet, and the link back to the original recipe for credit.

Run from the backend folder, after scripts/import_indb.py:
    .venv/bin/python scripts/match_mendeley.py
Downloads the CSV the first time, writes app/data/mendeley_matches.json, and prints samples to check.
"""
import csv
import json
import random
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
CACHE = BACKEND / "scripts" / ".mendeley"  # downloaded CSV, not committed
DATA = BACKEND / "app" / "data"
CSV_URL = ("https://data.mendeley.com/public-files/datasets/xsphgmmh7b/files/"
           "6fb5ae32-a815-4b8f-9d68-8d512227eac8/file_downloaded")

# Words that say nothing about which dish it is
FILLER = set("""recipe recipes how to make made style homemade home easy quick healthy delicious simple classic
traditional authentic indian special tasty perfect best instant restaurant dhaba with and or in of a an the
for ka ki ke wali wala vali vala spicy hot style simple version""".split())
# Different spellings of the same dish word
DISH_WORDS = {
    "sabzi": "sabji subji sabzi subzi sabjee sabjiyan",
    "khichdi": "khichri khitchdi khichdi khichadi kichdi khichari",
    "pulao": "pulav pilaf pulao pullao pilau",
    "paratha": "parantha paratha prantha parotha",
    "raita": "raita raitha",
    "halwa": "halwa halva",
    "pakora": "pakoda pakora pakode pakore pakodi bhajiya bhajji",
    "ladoo": "laddu ladoo laddoo ladu laddus",
    "barfi": "burfi barfi",
    "chutney": "chutney chatni",
    "curry": "curry kari gravy",
    "dal": "dal daal dhal dhall",
    "kebab": "kabab kebab kabob kebabs",
    "biryani": "biryani biriyani briyani",
    "dosa": "dosa dosai dose",
    "idli": "idli idly",
    "upma": "upma uppittu",
    "kadhi": "kadhi",
    "tadka": "tadka tarka tadkewali",
    "chilla": "chilla cheela chila",
    "bhatura": "bhatura bhature",
    "puri": "puri poori",
    "roti": "roti chapati chapatti phulka",
    "kofta": "kofta koftas kofte",
    "korma": "korma kurma",
    "keema": "keema kheema qeema kima",
    "makhani": "makhani makhanwala",
    "tikki": "tikki tikkiya",
    "sandwich": "sandwich sandwiches",
    "cutlet": "cutlet cutlets",
    "soup": "soup shorba",
    "pickle": "pickle pickled achar achaar",
    "fry": "fry fried",
    "milkshake": "milkshake shake",
}
WORD_TO_DISH = {w: k for k, words in DISH_WORDS.items() for w in words.split()}
# Words that say what kind of dish it is. Two names must agree on these to be the same dish.
DISH_TYPES = set(DISH_WORDS) | set("""saag biryani rice noodles pasta pizza burger roll chaat salad sauce cake cookie
biscuit pudding kulfi ice cream jam tea coffee lassi sharbat juice naan kulcha tikka masala bharta stew stock
yakhni bhaji sizzler porridge""".split())
# Mendeley's diet labels, as INDB's veg / egg / non_veg
MENDELEY_DIET = {"Non Vegeterian": "non_veg", "High Protein Non Vegetarian": "non_veg", "Eggetarian": "egg"}


def ingredient_phrases(for_names=False):
    """Every way people write an ingredient, mapped to its id, longest first.

    For dish names, family rows (millet, berries) are left out, so jowar and ragi stay different words.
    """
    pairs = []
    for ing in json.loads((DATA / "ingredients.json").read_text(encoding="utf-8")):
        if "additive" in ing["labels"] or (for_names and "group" in ing["labels"]):
            continue
        for s in ing["spellings"] + [ing["names"]["en"]]:
            pairs.append((clean(s), ing["id"]))
    pairs += [("ladies finger", "okra"), ("ladys finger", "okra"), ("lady finger", "okra"),
              ("ladies fingers", "okra"), ("ladys fingers", "okra"), ("cottage cheese", "paneer"),
              ("chana", "chole"), ("channa", "chole"), ("gobi", "cauliflower"), ("dahi", "curd")]
    return sorted({p for p in pairs if p[0]}, key=lambda p: -len(p[0]))


def clean(text):
    text = text.lower().replace("&", " and ").replace("'", "")
    return re.sub(r"[^a-z0-9 ]+", " ", text).strip()


def tokens(text, phrases):
    """The words that identify a dish, with ingredient and dish spellings made the same."""
    text = f" {clean(text)} "
    for phrase, ing_id in phrases:
        text = text.replace(f" {phrase} ", f" @{ing_id} ")
    words = set()
    for w in text.split():
        w = WORD_TO_DISH.get(w, w)
        if w not in FILLER and not w.isdigit() and len(w) > 1:
            words.add(w)
    return words


def dice(a, b):
    return 2 * len(a & b) / (len(a) + len(b)) if a and b else 0.0


def same_kind(a, b):
    """Handi chicken is not handi biryani: if the Mendeley name says a dish type, INDB's must share it."""
    ta, tb = a & DISH_TYPES, b & DISH_TYPES
    if ta and tb:
        return bool(ta & tb)
    return not tb


def number(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "IndianFoodDatasetCSV.csv"
    if not path.exists():
        print("downloading the Mendeley CSV (24 MB)")
        urllib.request.urlretrieve(CSV_URL, path)
    csv.field_size_limit(10 ** 8)
    with open(path, encoding="utf-8", errors="replace") as f:
        mendeley = list(csv.DictReader(f))

    phrases = ingredient_phrases()
    name_phrases = ingredient_phrases(for_names=True)
    labels = {i["id"]: set(i["labels"]) for i in json.loads((DATA / "ingredients.json").read_text(encoding="utf-8"))}
    indb = json.loads((DATA / "indb_recipes.json").read_text(encoding="utf-8"))["recipes"]

    # Mendeley: name tokens from both halves of "Masala Bhindi Recipe - Spicy Okra Stir Fry", ingredients as ids
    m_items = []
    for row in mendeley:
        name = row["TranslatedRecipeName"] or row["RecipeName"]
        ings = {w[1:] for w in tokens(row["TranslatedIngredients"] or "", phrases) if w.startswith("@")}
        diet = MENDELEY_DIET.get(row["Diet"], "veg")
        m_items.append((row, tokens(name.split(" - ")[0], name_phrases), tokens(name, name_phrases), ings, diet))

    matches = {}
    for dish in indb:
        name_tokens = tokens(f"{dish['name']} {dish['local_name'] or ''}".replace("/", " "), name_phrases)
        main_ings = {i["id"] for i in dish["ingredients"]
                     if not labels.get(i["id"], set()) & {"pantry", "garnish", "additive", "fat"}}
        best = None
        for row, head, full, m_ings, m_diet in m_items:
            if m_diet != dish["diet"]:
                continue  # never let a veg dish borrow facts from an egg or meat one
            name_score, best_half = max((dice(name_tokens, head), head), (dice(name_tokens, full), full),
                                        key=lambda x: x[0])
            # The dish type is checked against Mendeley's whole name ("Sprouted Moong Dal - ... Curry")
            if name_score < 0.5 or not same_kind(name_tokens, full):
                continue
            # A one-word Mendeley name ("Hot chicken") matches too easily, unless it is the same name
            if len(best_half) < 2 and name_score < 1:
                continue
            # Ingredients named in the INDB dish name must be in the Mendeley name too (suji is not dalia)
            if not {w for w in name_tokens if w.startswith("@")} <= full:
                continue
            ing_score = len(main_ings & m_ings) / len(main_ings) if main_ings else 1.0
            # Close names count only if the main ingredients agree too
            ok = name_score >= 0.8 and ing_score >= 0.5 or name_score >= 0.6 and ing_score >= 0.75
            score = name_score + 0.5 * ing_score
            exact = name_tokens == head or name_tokens == full
            if ok and (best is None or score > best[0]):
                best = (score, row, name_score, ing_score, exact)
        if best:
            _, row, name_score, ing_score, exact = best
            matches[dish["id"]] = {
                "mendeley_name": (row["TranslatedRecipeName"] or row["RecipeName"]).strip(),
                "prep_min": number(row["PrepTimeInMins"]),
                "cook_min": number(row["CookTimeInMins"]),
                "total_min": number(row["TotalTimeInMins"]),
                "course": row["Course"],
                "cuisine": row["Cuisine"],
                "diet": row["Diet"],
                "url": row["URL"].strip(),
                "match": "same" if exact else "close",
                "name_score": round(name_score, 2),
                "ingredient_score": round(ing_score, 2),
            }

    (DATA / "mendeley_matches.json").write_text(json.dumps({
        "credit": "Cooking times, course and cuisine: 6000+ Indian Food Recipes Dataset, Kanishka Jain (2020), "
                  "Mendeley Data, doi:10.17632/xsphgmmh7b.1, CC BY 4.0, built from archanaskitchen.com. "
                  "Only these facts and the link are kept; no ingredient or step text.",
        "matches": matches,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    kinds = Counter(d["kind"] for d in indb if d["id"] in matches)
    print(f"{len(matches)} of {len(indb)} INDB dishes found in Mendeley ({len(mendeley)} recipes)")
    print("by kind:", dict(kinds))
    print("same name:", sum(m["match"] == "same" for m in matches.values()), "| close variant:",
          sum(m["match"] == "close" for m in matches.values()))
    random.seed(1)
    names = {d["id"]: f"{d['name']}" + (f" ({d['local_name']})" if d["local_name"] else "") for d in indb}
    print("\nrandom sample to check by eye:")
    for code in random.sample(sorted(matches), min(40, len(matches))):
        m = matches[code]
        print(f"  {names[code][:48]:48} -> {m['mendeley_name'][:60]:60} [{m['name_score']}, {m['ingredient_score']}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())

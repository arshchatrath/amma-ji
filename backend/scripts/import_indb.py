"""Turns the Indian Nutrient Databank (INDB) spreadsheets into Amma ji's dish catalogue.

INDB: Vijayakumar A, Dubasi HB, Awasthi A, Jaacks LM. Curr Dev Nutr 2024;8(7):103790.
Data: https://github.com/lindsayjaacks/Indian-Nutrient-Databank-INDB-
INDB gives each dish's ingredients, amounts, servings and nutrition. It has no cooking steps.

Run from the backend folder (needs openpyxl from requirements-dev.txt):
    .venv/bin/python scripts/import_indb.py
Downloads the spreadsheets the first time, then writes app/data/indb_recipes.json and
app/data/ingredients.json, and prints how many INDB ingredients the table could not place.
"""
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

from ingredient_table import TABLE

BACKEND = Path(__file__).resolve().parent.parent
CACHE = BACKEND / "scripts" / ".indb"  # downloaded spreadsheets, not committed
DATA = BACKEND / "app" / "data"
REPO = "https://raw.githubusercontent.com/lindsayjaacks/Indian-Nutrient-Databank-INDB-/main/"
FILES = ["recipes.xlsx", "recipes_names.xlsx", "recipes_servingsize.xlsx", "INDB.xlsx", "recipe_links.xlsx"]
SOURCES = {
    "asc_manual": "The Art & Science of Cooking, 5th ed. (Khanna et al., 2007), via INDB",
    "bfp_manual": "Basic Food Preparation, 4th ed. (Raina et al., 2011), via INDB",
    "open_source_recipes": "Food blog recipe, via INDB",
}
# Rough grams per unit, only used to tell main ingredients from small ones
GRAMS = {"g": 1, "ml": 1, "tsp": 5, "tbsp": 15, "C": 240, "sprig": 2, "pinch": 0.5, "nos": 50,
         "drops": 0.05, "sheet": 1}
UNIT_NAMES = {"C": "cup", "nos": "piece"}
ALLERGENS = {"dairy", "gluten", "nuts", "peanut", "egg", "fish", "shellfish", "soy", "sesame", "mustard"}
# What kind of dish, guessed from its name. The first match wins, so the order matters.
KINDS = [
    ("drink", r"\b(tea|chai|coffee|juice|sharbat|sherbet|shake|lassi|smoothie|squash|punch|cooler|drink|soda|"
              r"lemonade|thandai|kanji|mocktail|cocktail|panna|jaljeera|chaas|buttermilk|cocoa)\b"),
    ("dessert", r"(halwa|kheer|cake|pudding|ice ?cream|kulfi|lad+o+|laddu|barfi|burfi|jamun|rasgul+a|rasmalai|jalebi|"
                r"cookie|biscuit|\btart|\bpie\b|custard|mousse|souffle|trifle|payasam|sheera|murabba|\bjam\b|jelly|"
                r"marmalade|candy|toffee|fudge|brownie|muffin|doughnut|meringue|sundae|phirni|firni|shrikhand|malpua|"
                r"gujiya|peda|sandesh|chikki|kalakand|petha|dessert|icing|sweet\b|mithai)"),
    ("side", r"(chutney|raita|pickle|achar|sauce|\bdip\b|dressing|stock|salad|relish|ketchup|papad)"),
    ("soup", r"(soup|shorba|rasam)"),
    ("bread", r"(roti|paratha|parantha|naan|\bpuri|poori|kulcha|bhatura|chapat+i|thepla|phulka|bread|\bbuns?\b)"),
    ("snack", r"(pakora|pakoda|samosa|tikki|cutlet|chaat|sandwich|toast|\bvada|wada|bhaji|chil+a\b|cheela|dhokla|"
              r"kachori|bhel|\bpuff|\broll|frankie|fritter|finger|nugget|popcorn|namkeen|mathri|chips|pizza|burger|"
              r"momo|canape|vol-au-vent|kebab|kabab|tikka)"),
]


def download():
    CACHE.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        path = CACHE / name
        if not path.exists():
            print(f"downloading {name}")
            urllib.request.urlretrieve(REPO + name, path)


def rows(name):
    sheet = load_workbook(CACHE / name, read_only=True).worksheets[0]
    it = sheet.iter_rows(values_only=True)
    head = [str(h).strip() if h is not None else "" for h in next(it)]
    return [dict(zip(head, r)) for r in it if any(c is not None for c in r)]


def ingredient_rules():
    rules, catalogue = [], []
    for ing_id, en, hi, pa, spellings, pattern, labels in TABLE:
        labels = labels.split()
        catalogue.append({"id": ing_id, "names": {"en": en, "hi": hi, "pa": pa},
                          "spellings": [s for s in spellings.split("|") if s], "labels": labels})
        if pattern:
            rules.append((re.compile(pattern), ing_id, set(labels)))
    return rules, catalogue


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def split_name(name):
    """'Okra fry (Bhindi sabzi)' -> ('Okra fry', 'Bhindi sabzi')"""
    m = re.match(r"^(.*?)\s*\((.+)\)\s*$", name.strip())
    return (m.group(1).strip(), m.group(2).strip()) if m else (name.strip(), None)


def main():
    download()
    rules, catalogue = ingredient_rules()
    labels_of = {c["id"]: set(c["labels"]) for c in catalogue}
    names = {r["recipe_code"]: r for r in rows("recipes_names.xlsx")}
    servings = {r["recipe_code"]: r for r in rows("recipes_servingsize.xlsx")}
    nutrition = {r["food_code"]: r for r in rows("INDB.xlsx")}
    links = {r["Food Code"]: str(r["Link"]).strip() for r in rows("recipe_links.xlsx") if r.get("Link")}

    by_recipe, unmapped, mapped_rows = {}, Counter(), 0
    for r in rows("recipes.xlsx"):
        food = str(r["food_name"] or r["food_name_org"] or "").strip()
        key = food.lower()
        found = next(((ing_id, labels) for rx, ing_id, labels in rules if rx.search(key)), None)
        if found:
            mapped_rows += 1
            ing_id, labels = found
        else:
            unmapped[food] += 1
            ing_id = "x_" + re.sub(r"[^a-z0-9]+", "_", key.split("(")[0]).strip("_")
            labels = set()
        amount, unit = number(r["amount"]), str(r["unit"] or "").strip()
        by_recipe.setdefault(r["recipe_code"], []).append({
            "id": ing_id,
            "as_written": str(r["ingredient_name_org"] or food).strip(),
            "qty": round(amount, 2) if amount is not None else None,
            "unit": UNIT_NAMES.get(unit, unit),
            "grams": round((amount or 0) * GRAMS.get(unit, 0), 1),
            "_labels": labels,
        })

    recipes = []
    for code, items in by_recipe.items():
        info = names.get(code, {})
        name, local = split_name(str(info.get("recipe_name") or code))
        # Main ingredients: not pantry, garnish or additive, and a real share of the dish by weight
        countable = [i for i in items if not i["_labels"] & {"pantry", "garnish", "additive", "fat"}]
        total = sum(i["grams"] for i in countable) or 1
        for i in items:
            i["essential"] = i in countable and (
                i["grams"] / total >= 0.15 or bool(i["_labels"] & {"meat", "fish", "egg"}))
        if countable and not any(i["essential"] for i in items):
            max(countable, key=lambda i: i["grams"])["essential"] = True
        labels = set().union(*(i.pop("_labels") for i in items))
        diet = "non_veg" if labels & {"meat", "fish", "gelatine"} else "egg" if "egg" in labels else "veg"
        text = f"{name} {local or ''}".lower()
        kind = next((k for k, rx in KINDS if re.search(rx, text)), "main")
        size = servings.get(code, {})
        n = nutrition.get(code, {})
        per_serving = number(n.get("unit_serving_energy_kcal")) is not None
        prefix = "unit_serving_" if per_serving else ""
        recipes.append({
            "id": code,
            "name": name,
            "local_name": local,
            "kind": kind,
            "diet": diet,
            "allergens": sorted(labels & ALLERGENS),
            "alcohol": "alcohol" in labels,
            "servings": {"count": number(size.get("no_of_servings")), "size": number(size.get("size_of_servings")),
                         "unit": size.get("servings_unit")},
            "ingredients": items,
            "nutrition": {
                "per": (f"1 {n.get('servings_unit') or size.get('servings_unit') or 'serving'}" if per_serving else "100 g"),
                **{key: round(number(n.get(prefix + col)) or 0, 1) for key, col in
                   (("kcal", "energy_kcal"), ("protein_g", "protein_g"), ("carbs_g", "carb_g"),
                    ("fat_g", "fat_g"), ("fibre_g", "fibre_g"))},
                "source": "INDB",
                "is_estimate": True,
            },
            "source": SOURCES.get(info.get("primarysource"), "INDB"),
            "source_link": links.get(code),
        })

    recipes.sort(key=lambda r: r["id"])
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "indb_recipes.json").write_text(json.dumps({
        "credit": "Ingredients and nutrition: Indian Nutrient Databank (INDB), Vijayakumar A, Dubasi HB, "
                  "Awasthi A, Jaacks LM. Curr Dev Nutr 2024;8(7):103790. Nutrition values are estimates.",
        "recipes": recipes,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (DATA / "ingredients.json").write_text(json.dumps(catalogue, ensure_ascii=False, indent=1), encoding="utf-8")

    total_rows = mapped_rows + sum(unmapped.values())
    print(f"{len(recipes)} dishes, {total_rows} ingredient rows, {mapped_rows / total_rows:.1%} placed in the table")
    print("kinds:", dict(Counter(r["kind"] for r in recipes)))
    print("diet:", dict(Counter(r["diet"] for r in recipes)))
    print("nutrition per serving:", sum(r["nutrition"]["per"] != "100 g" for r in recipes), "of", len(recipes))
    if unmapped:
        print(f"\nnot in the table ({len(unmapped)} foods, kept under their INDB name):")
        for food, count in unmapped.most_common():
            print(f"  {count:4d}  {food}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

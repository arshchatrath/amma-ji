"""Load the recipe sheet (app/data/catalogue.json) into Supabase.

Run supabase/schema.sql once in the Supabase SQL editor, then from backend/:
  SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... .venv/bin/python scripts/push_supabase.py
The URL and key come only from the environment (or backend/.env). Nothing is written to disk.
Rows are upserted, so running it again after a rebuild just updates them.
  --dry-run   count the rows without sending anything
"""
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
CATALOGUE = BACKEND / "app" / "data" / "catalogue.json"
BATCH = 500


def rows():
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    tables = {"dishes": [], "dish_ingredients": [], "steps": [], "mistakes": []}
    for r in data["recipes"]:
        tables["dishes"].append({
            "id": r["id"], "name_en": r["name"]["en"], "name_hinglish": r["name"]["hi-en"],
            "name_hi": r["name"]["hi"], "name_pa": r["name"]["pa"], "kind": r["kind"], "diet": r["diet"],
            "allergens": r["allergens"], "servings": r["servings"], "prep_min": r["prep_min"],
            "cook_min": r["cook_min"], "total_min": r["total_min"], "course": r["course"], "cuisine": r["cuisine"],
            "nutrition_per_serving": r["nutrition_per_serving"], "has_steps": r["has_steps"],
            "source_link": r["source_link"], "source_note": r["source_note"]})
        for n, i in enumerate(r["ingredients"], 1):
            tables["dish_ingredients"].append({
                "dish_id": r["id"], "n": n, "ingredient_id": i["id"], "as_written": i["as_written"],
                "qty": i["qty"], "unit": i["unit"], "essential": i["essential"], "substitutes": i["substitutes"]})
        for s in r["steps"]:
            safety = s["safety"] or {}
            tables["steps"].append({
                "dish_id": r["id"], "n": s["n"], "text_en": s["text"]["en"], "text_hinglish": s["text"]["hi-en"],
                "text_hi": s["text"]["hi"], "text_pa": s["text"]["pa"], "uses": s["uses"],
                "timer_min": s["timer_min"], "safety_en": safety.get("en"), "safety_hinglish": safety.get("hi-en"),
                "safety_hi": safety.get("hi"), "safety_pa": safety.get("pa")})
        for n, m in enumerate(r["common_mistakes"], 1):
            tables["mistakes"].append({"dish_id": r["id"], "n": n, "mistake": m["mistake"],
                                       "fix_en": m["fix"]["en"], "fix_hi": m["fix"]["hi"]})
    return tables


KEYS = {"dishes": "id", "dish_ingredients": "dish_id,n", "steps": "dish_id,n", "mistakes": "dish_id,n"}


def main():
    tables = rows()
    if "--dry-run" in sys.argv:
        for name, items in tables.items():
            print(f"{name}: {len(items)} rows")
        return 0
    load_dotenv(BACKEND / ".env")
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment or backend/.env first.")
        return 1
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "Prefer": "resolution=merge-duplicates,return=minimal"}
    for name, items in tables.items():  # dishes first, so the other tables can point at them
        for start in range(0, len(items), BATCH):
            r = requests.post(f"{url.rstrip('/')}/rest/v1/{name}", params={"on_conflict": KEYS[name]},
                              headers=headers, json=items[start:start + BATCH], timeout=60)
            if r.status_code >= 300:
                print(f"{name}: Supabase said {r.status_code}: {r.text[:300]}")
                return 1
        print(f"{name}: {len(items)} rows sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())

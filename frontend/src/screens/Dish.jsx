import { useEffect, useState } from "react";
import { api } from "../api.js";
import { canTalk, hush, sayLine } from "../audio/voice.js";
import Nutrition from "../components/Nutrition.jsx";
import "./Dish.css";

function amount(i) {
  if (i.qty == null) return "";
  const qty = Number.isInteger(i.qty) ? i.qty : Math.round(i.qty * 100) / 100;
  return `${qty} ${i.unit || ""}`.trim();
}

// Flow D: the recipe card. Nutrition is an estimate from INDB, never written by the AI.
export default function Dish({ id, language, onCook, onBack, starting }) {
  const [dish, setDish] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.recipe(id, language).then(setDish, (e) => setError(e.message));
  }, [id, language]);

  // Amma ji approves the pick. She stops if the cook leaves or starts cooking.
  useEffect(() => {
    if (canTalk()) sayLine("ready", language).catch(() => {});
    return hush;
  }, [id, language]);

  if (error) {
    return (
      <main className="dish">
        <p className="pantry__error" role="alert">
          {error}
        </p>
        <button className="dishes__more" onClick={onBack}>
          Back to the dishes
        </button>
      </main>
    );
  }
  if (!dish) return <main className="dish" aria-busy="true" />;

  const n = dish.nutrition;
  return (
    <main className="dish" onPointerDown={hush}>
      <header className="dishes__top">
        <button className="round-button" onClick={onBack} aria-label="Back to the dishes">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M15 5l-7 7 7 7" />
          </svg>
        </button>
        <div>
          <h1 className="dish__name">{dish.name}</h1>
          <p className="dish__meta">
            {dish.minutes ? `${dish.minutes} min` : ""}
            {dish.diet === "veg" ? ", veg" : dish.diet === "egg" ? ", has egg" : ", non-veg"}
            {dish.allergens.length ? `, contains ${dish.allergens.join(", ")}` : ""}
          </p>
        </div>
      </header>

      <section>
        <h2>Ingredients</h2>
        <ul className="dish__ingredients">
          {dish.ingredients.map((i) => (
            <li key={i.id} className={i.essential ? "is-essential" : ""}>
              <span>
                {i.name}
                {i.essential && <span className="visually-hidden"> (must have)</span>}
              </span>
              <span className="dish__qty">{amount(i)}</span>
              {i.substitutes.length > 0 && (
                <span className="dish__swap">
                  or {i.substitutes.map((s) => (s === "skip" ? "skip it" : s)).join(", ")}
                </span>
              )}
            </li>
          ))}
        </ul>
        <p className="dish__note">Bold ones are must-haves.</p>
      </section>

      <section>
        <h2>Steps</h2>
        <ol className="dish__steps">
          {dish.steps.map((s, k) => (
            <li key={k}>{s}</li>
          ))}
        </ol>
      </section>

      {n && <Nutrition n={n} />}

      <p className="dish__source">
        {dish.source_note}{" "}
        {dish.source_link && (
          <a href={dish.source_link} target="_blank" rel="noreferrer">
            Original recipe
          </a>
        )}
      </p>

      <button className="big-button dish__cook" onClick={() => onCook(dish.id)} disabled={starting}>
        {starting ? "Getting the kadhai ready" : "Cook this with Amma ji"}
      </button>
    </main>
  );
}

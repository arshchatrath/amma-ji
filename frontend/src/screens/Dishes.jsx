import { useEffect, useState } from "react";
import { api } from "../api.js";
import "./Dishes.css";

const LABELS = {
  can_make_now: "Can make now",
  needs_one_optional: "Needs 1 optional item",
  needs_optional: "Some optional items missing",
  missing_essential: "Missing an essential",
};

// Flow C: the best dishes for what you have, ranked by code (not AI), with honest labels.
export default function Dishes({ language, pantry, onOpen, onBack }) {
  const [dishes, setDishes] = useState(null);
  const [limit, setLimit] = useState(3);
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");
    api
      .suggest({
        have: pantry.have.map((i) => i.id),
        not_have: pantry.notHave.map((i) => i.id),
        minutes: pantry.minutes,
        diet: pantry.veg ? "veg" : null,
        allergies: pantry.allergies,
        language,
        limit,
      })
      .then(setDishes, (e) => setError(e.message));
  }, [pantry, language, limit]);

  return (
    <main className="dishes">
      <header className="dishes__top">
        <button className="round-button" onClick={onBack} aria-label="Back to your ingredients">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M15 5l-7 7 7 7" />
          </svg>
        </button>
        <h1>Amma ji suggests</h1>
      </header>

      {error && (
        <p className="pantry__error" role="alert">
          {error}
        </p>
      )}
      {dishes && !dishes.length && (
        <p className="dishes__none">
          Nothing fits yet. Add a few more things you have, or take out a filter.
        </p>
      )}

      <ol className="dishes__list">
        {(dishes || []).map((d, n) => (
          <li key={d.id}>
            <button className={`dish-card dish-card--${d.label}`} onClick={() => onOpen(d.id)}>
              <span className="dish-card__rank" aria-hidden="true">
                {n + 1}
              </span>
              <span className={`dish-card__label label--${d.label}`}>{LABELS[d.label]}</span>
              <span className="dish-card__name">{d.name}</span>
              <span className="dish-card__why">{d.why}</span>
              <span className="dish-card__facts">
                {d.minutes ? `${d.minutes} min` : "Time not known"}
                {d.longer_than_you_have ? ", longer than you have" : ""}
                {d.kcal ? `, about ${Math.round(d.kcal)} kcal per ${(d.nutrition_per || "serving").replace(/^1 /, "")}` : ""}
                {d.diet !== "veg" ? (d.diet === "egg" ? ", has egg" : ", non-veg") : ""}
              </span>
            </button>
          </li>
        ))}
      </ol>

      {dishes && dishes.length === limit && limit < 10 && (
        <button className="dishes__more" onClick={() => setLimit(10)}>
          Show more dishes
        </button>
      )}
    </main>
  );
}

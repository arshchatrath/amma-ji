import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { unlockAudio } from "../audio/context.js";
import { startRecording } from "../audio/recorder.js";
import Kadhai from "../components/Kadhai.jsx";
import "./Dishes.css";

const LABELS = {
  can_make_now: "Can make now",
  needs_one_optional: "Needs 1 optional item",
  needs_optional: "Some optional items missing",
  missing_essential: "Missing an essential",
};

const STATUS = {
  idle: "Tap and say which one, like \"doosra wala\"",
  listening: "Listening. Tap again when you finish",
  thinking: "Amma ji is looking",
};

// Flow C: the best dishes for what you have, ranked by code (not AI), with honest labels.
// Pick one by tapping it, or by voice: "doosra wala", "number 3", "aloo paratha wala".
export default function Dishes({ language, pantry, onOpen, onBack }) {
  const [dishes, setDishes] = useState(null);
  const [limit, setLimit] = useState(3);
  const [error, setError] = useState("");
  const [mood, setMood] = useState("idle");
  const [heard, setHeard] = useState("");
  const recording = useRef(null);

  async function listen() {
    const context = unlockAudio();
    if (mood === "listening") return recording.current?.stop();
    if (mood !== "idle") return;
    setError("");
    try {
      setMood("listening");
      recording.current = await startRecording(context);
      const wav = await recording.current.result;
      recording.current = null;
      if (!wav) return setError("Amma ji did not hear anything. Tap and speak a little closer.");
      setMood("thinking");
      const { text } = await api.hear(wav, language);
      setHeard(text);
      const { id } = await api.pick(text, dishes.map((d) => d.id));
      if (id) return onOpen(id);
      setError("Amma ji could not tell which one. Say its number, like \"pehla wala\", or tap it.");
    } catch (e) {
      setError(e.name === "NotAllowedError" ? "Amma ji needs the microphone. Allow it, or tap a dish." : e.message);
    } finally {
      setMood("idle");
    }
  }

  useEffect(() => () => recording.current?.stop(), []);

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
      {dishes?.length > 0 && (
        <section className="pantry__voice dishes__voice">
          <button className={`pantry__mic pantry__mic--${mood}`} onClick={listen} aria-label="Say which dish">
            <Kadhai mood={mood} size={76} />
          </button>
          <div>
            <p className="pantry__status" aria-live="polite">
              {STATUS[mood]}
            </p>
            {mood === "listening" && <span className="pantry__mic-on">Mic on</span>}
            {heard && mood === "idle" && <p className="pantry__example">Heard: "{heard}"</p>}
          </div>
        </section>
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

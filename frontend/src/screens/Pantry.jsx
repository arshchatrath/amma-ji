import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { unlockAudio } from "../audio/context.js";
import { startRecording } from "../audio/recorder.js";
import Kadhai from "../components/Kadhai.jsx";
import "./Pantry.css";

const TIMES = [null, 15, 30, 45];
const ALLERGIES = [
  ["peanut", "Peanuts"],
  ["nuts", "Nuts"],
  ["dairy", "Milk"],
  ["gluten", "Wheat"],
  ["egg", "Egg"],
  ["fish", "Fish"],
  ["shellfish", "Prawns"],
  ["soy", "Soy"],
  ["sesame", "Til"],
  ["mustard", "Mustard"],
];
const STATUS = {
  idle: "Tap the kadhai and tell Amma ji what you have",
  listening: "Listening. Tap again when you finish",
  thinking: "Amma ji is checking your kitchen",
};

function addUnique(list, items) {
  const ids = new Set(list.map((i) => i.id));
  return [...list, ...items.filter((i) => !ids.has(i.id))];
}

// Flow B: tell Amma ji what is in the kitchen. Chips can be fixed by tapping.
export default function Pantry({ language, pantry, setPantry, onFind, onBack }) {
  const [mood, setMood] = useState("idle");
  const [heard, setHeard] = useState("");
  const [typed, setTyped] = useState("");
  const [extra, setExtra] = useState("");
  const [known, setKnown] = useState([]);
  const [error, setError] = useState("");
  const recording = useRef(null);

  useEffect(() => {
    api.ingredients(language).then(setKnown, () => setKnown([]));
  }, [language]);

  // Merge what was said into the chips: new things to have, things said to be missing
  async function understand(text) {
    setHeard(text);
    const result = await api.pantry(text, language);
    setPantry((p) => ({
      ...p,
      have: addUnique(p.have.filter((i) => !result.not_have.some((n) => n.id === i.id)), result.have),
      notHave: addUnique(p.notHave, result.not_have),
      minutes: result.minutes ?? p.minutes,
      veg: result.diet === "veg" ? true : p.veg,
    }));
    if (!result.have.length && !result.not_have.length) {
      setError("Amma ji did not catch any ingredients. Try saying them one by one, or type them below.");
    }
  }

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
      if (!wav) {
        setMood("idle");
        return setError("Amma ji did not hear anything. Tap the kadhai and speak a little closer.");
      }
      setMood("thinking");
      const { text } = await api.hear(wav, language);
      await understand(text);
    } catch (e) {
      setError(e.name === "NotAllowedError" ? "Amma ji needs the microphone. Allow it, or type below." : e.message);
    } finally {
      setMood("idle");
    }
  }

  async function send(event) {
    event.preventDefault();
    if (!typed.trim()) return;
    setError("");
    setMood("thinking");
    try {
      await understand(typed.trim());
      setTyped("");
    } catch (e) {
      setError(e.message);
    } finally {
      setMood("idle");
    }
  }

  function addByName(event) {
    event.preventDefault();
    const match = known.find((k) => k.name.toLowerCase() === extra.trim().toLowerCase());
    if (!match) return setError(`Amma ji does not know "${extra}" yet. Pick one from the list.`);
    setPantry((p) => ({ ...p, have: addUnique(p.have, [match]), notHave: p.notHave.filter((n) => n.id !== match.id) }));
    setExtra("");
    setError("");
  }

  const remove = (id) => setPantry((p) => ({ ...p, have: p.have.filter((i) => i.id !== id) }));
  const toggleAllergy = (id) =>
    setPantry((p) => ({
      ...p,
      allergies: p.allergies.includes(id) ? p.allergies.filter((a) => a !== id) : [...p.allergies, id],
    }));

  return (
    <main className="pantry">
      <header className="pantry__top">
        <button className="round-button" onClick={onBack} aria-label="Back to the start">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M15 5l-7 7 7 7" />
          </svg>
        </button>
        <h1>What's in your kitchen?</h1>
      </header>

      <section className="pantry__voice">
        <button className={`pantry__mic pantry__mic--${mood}`} onClick={listen} aria-label="Tell Amma ji what you have">
          <Kadhai mood={mood} size={128} />
        </button>
        <div>
          <p className="pantry__status" aria-live="polite">
            {STATUS[mood]}
          </p>
          <p className="pantry__example">Like: "Do aloo, paneer, pyaaz hai. 20 minute mein kuch bana do."</p>
          {mood === "listening" && <span className="pantry__mic-on">Mic on</span>}
        </div>
      </section>

      <form className="pantry__type" onSubmit={send}>
        <label className="visually-hidden" htmlFor="pantry-type">
          Type what you have
        </label>
        <input
          id="pantry-type"
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          placeholder="Or type: aloo, paneer, pyaaz..."
          autoComplete="off"
        />
        <button type="submit" disabled={!typed.trim() || mood !== "idle"}>
          Add
        </button>
      </form>

      {heard && <p className="pantry__heard">Heard: "{heard}"</p>}
      {error && (
        <p className="pantry__error" role="alert">
          {error}
        </p>
      )}

      <section aria-label="What you have">
        <h2>You have</h2>
        {pantry.have.length ? (
          <ul className="chips">
            {pantry.have.map((i) => (
              <li key={i.id}>
                <button className="chip" onClick={() => remove(i.id)} aria-label={`Remove ${i.name}`}>
                  {i.name}
                  <span aria-hidden="true">×</span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="pantry__empty">Nothing yet. Salt, oil and everyday masalas are counted already.</p>
        )}
        {pantry.notHave.length > 0 && (
          <p className="pantry__missing">Not there: {pantry.notHave.map((i) => i.name).join(", ")}</p>
        )}
        <form className="pantry__add" onSubmit={addByName}>
          <label className="visually-hidden" htmlFor="pantry-add">
            Add one ingredient
          </label>
          <input
            id="pantry-add"
            list="known-ingredients"
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
            placeholder="Add one more"
            autoComplete="off"
          />
          <datalist id="known-ingredients">
            {known.map((k) => (
              <option key={k.id} value={k.name} />
            ))}
          </datalist>
          <button type="submit" disabled={!extra.trim()}>
            Add
          </button>
        </form>
      </section>

      <section aria-label="Time">
        <h2>How much time?</h2>
        <div className="choice-row" role="radiogroup">
          {TIMES.map((t) => (
            <button
              key={t ?? "any"}
              role="radio"
              aria-checked={pantry.minutes === t}
              className={`choice${pantry.minutes === t ? " is-on" : ""}`}
              onClick={() => setPantry((p) => ({ ...p, minutes: t }))}
            >
              {t ? `${t} min` : "Any"}
            </button>
          ))}
        </div>
      </section>

      <section aria-label="Diet and allergies">
        <h2>Anything to keep out?</h2>
        <div className="choice-row">
          <button
            aria-pressed={pantry.veg}
            className={`choice${pantry.veg ? " is-on" : ""}`}
            onClick={() => setPantry((p) => ({ ...p, veg: !p.veg }))}
          >
            Veg only
          </button>
          {ALLERGIES.map(([id, label]) => (
            <button
              key={id}
              aria-pressed={pantry.allergies.includes(id)}
              className={`choice choice--allergy${pantry.allergies.includes(id) ? " is-on" : ""}`}
              onClick={() => toggleAllergy(id)}
            >
              No {label.toLowerCase()}
            </button>
          ))}
        </div>
      </section>

      <button className="big-button" onClick={onFind} disabled={!pantry.have.length}>
        Show me dishes
      </button>
    </main>
  );
}

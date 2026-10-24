import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { unlockAudio } from "../audio/context.js";
import { playStream } from "../audio/player.js";
import Nutrition from "../components/Nutrition.jsx";
import "./Finish.css";

const RATINGS = [
  ["loved", "Loved it"],
  ["okay", "It was okay"],
  ["bad", "Didn't turn out well"],
];

// Flow F: the dish is ready. What you made, what you changed, and "how was it?"
export default function Finish({ summary, sessionId, onAgain, onHome }) {
  const [rating, setRating] = useState(summary.feedback);
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState("");
  const playing = useRef(null);

  async function say(line) {
    playing.current?.stop();
    try {
      const context = unlockAudio();
      const player = playStream(await api.speak(line.speak, summary.language), context);
      playing.current = player;
      await player.done;
    } catch {
      // her voice is a nice extra here: the words are on screen anyway
    }
  }

  useEffect(() => {
    say(summary.closing);
    return () => playing.current?.stop();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function rate(value) {
    setRating(value);
    setError("");
    try {
      const reply = await api.feedback(sessionId, value);
      setAnswer(reply);
      say(reply.reply);
    } catch (e) {
      setError(e.status === 404 ? "" : e.message);
    }
  }

  return (
    <main className="finish">
      <header className="finish__top">
        <p className="finish__ready">Ready</p>
        <h1 className="finish__name">{summary.recipe_name}</h1>
        <p className="finish__time">Cooked in {summary.minutes} min</p>
      </header>

      <p className="finish__amma">{summary.closing.text}</p>

      {summary.changes.length > 0 && (
        <section>
          <h2>What you changed</h2>
          <ul className="finish__changes">
            {summary.changes.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </section>
      )}

      {summary.nutrition && <Nutrition n={summary.nutrition} />}

      <section aria-labelledby="how-was-it">
        <h2 id="how-was-it">How was it?</h2>
        <div className="choice-row">
          {RATINGS.map(([value, label]) => (
            <button
              key={value}
              aria-pressed={rating === value}
              className={`choice${rating === value ? " is-on" : ""}`}
              onClick={() => rate(value)}
            >
              {label}
            </button>
          ))}
        </div>
        {answer && <p className="finish__amma finish__amma--reply">{answer.reply.text}</p>}
        {answer?.tips.length > 0 && (
          <ul className="finish__tips">
            {answer.tips.map((t) => (
              <li key={t.problem}>
                <strong>{t.problem.charAt(0).toUpperCase() + t.problem.slice(1)}</strong>
                <span>{t.fix}</span>
              </li>
            ))}
          </ul>
        )}
        {error && (
          <p className="pantry__error" role="alert">
            {error}
          </p>
        )}
      </section>

      <div className="finish__actions">
        <button className="big-button" onClick={onAgain}>
          Cook something else
        </button>
        <button className="dishes__more" onClick={onHome}>
          Back to the start
        </button>
      </div>
    </main>
  );
}

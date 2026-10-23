import { useEffect, useRef, useState } from "react";
import Kadhai from "../components/Kadhai.jsx";
import { EXCHANGES, RECIPE } from "../data/dalTadka.js";
import "./Cooking.css";

const STATUS = {
  idle: 'Say "Amma ji" or tap the kadhai',
  listening: "Listening to you",
  thinking: "Amma ji is thinking",
  speaking: "Amma ji is speaking",
  muted: "Muted. Amma ji is not listening",
};

function clock(seconds) {
  const m = Math.floor(seconds / 60);
  const s = String(seconds % 60).padStart(2, "0");
  return `${m}:${s}`;
}

// Flow E: cooking mode. For now the voice turn is acted out with pretend data.
export default function Cooking({ language, onExit }) {
  const [step, setStep] = useState(3); // index, so this is step 4
  const [mood, setMood] = useState("idle");
  const [muted, setMuted] = useState(false);
  const [exchange, setExchange] = useState(0);
  const [left, setLeft] = useState(3 * 60);
  const turn = useRef([]);

  // Timers run in code, never in the AI's memory
  useEffect(() => {
    const id = setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => () => turn.current.forEach(clearTimeout), []);

  function stopTurn() {
    turn.current.forEach(clearTimeout);
    turn.current = [];
    setMood("idle");
  }

  // Pretend voice turn: listen, think, answer
  function talk() {
    if (muted) return setMuted(false);
    if (mood !== "idle") return stopTurn();
    setMood("listening");
    turn.current = [
      setTimeout(() => setMood("thinking"), 2000),
      setTimeout(() => {
        setExchange((e) => (e + 1) % EXCHANGES.length);
        setMood("speaking");
      }, 3100),
      setTimeout(() => setMood("idle"), 6200),
    ];
  }

  const total = RECIPE.steps.length;
  const current = RECIPE.steps[step];
  const shown = muted ? "muted" : mood;
  const line = EXCHANGES[exchange];

  return (
    <main className="cook">
      <header className="cook__top">
        <button className="cook__back" onClick={onExit} aria-label="Leave cooking mode">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7" /></svg>
        </button>
        <div className="cook__title">
          <h1>{RECIPE.name[language]}</h1>
          <p>
            Step {step + 1} of {total}
          </p>
        </div>
      </header>

      <ol className="cook__progress" aria-hidden="true">
        {RECIPE.steps.map((_, i) => (
          <li key={i} className={i < step ? "is-done" : i === step ? "is-now" : ""} />
        ))}
      </ol>

      <section className="cook__step" aria-live="polite">
        <p className="cook__step-text" key={step}>
          {current[language]}
        </p>
        {current.safety && (
          <p className="cook__safety">
            <strong>Careful: </strong>
            {current.safety[language]}
          </p>
        )}
      </section>

      <section className={`cook__timer${left === 0 ? " is-done" : ""}`} aria-label="Timer">
        <span className="cook__timer-label">{left === 0 ? "Dal simmer is done" : "Dal simmer"}</span>
        <span className="cook__timer-time">{clock(left)}</span>
        <span className="cook__timer-bar" style={{ "--left": left / 180 }} aria-hidden="true" />
      </section>

      <section className="cook__chat" aria-label="Last thing you said and her answer">
        <p className="cook__you">{line.you[language]}</p>
        <p className="cook__amma">{line.amma[language]}</p>
      </section>

      <p className="cook__note">Keep this screen open while cooking</p>

      <nav className="cook__dock" aria-label="Cooking controls">
        <p className="cook__status" aria-live="polite">
          {STATUS[shown]}
        </p>

        <div className="cook__row">
          <button
            className="cook__nav"
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
          >
            Back
          </button>

          <button
            className={`cook__mic cook__mic--${shown}`}
            onClick={talk}
            aria-label={muted ? "Unmute Amma ji" : mood === "idle" ? "Talk to Amma ji" : "Stop this turn"}
          >
            <Kadhai mood={shown} size={116} />
          </button>

          <button
            className="cook__nav"
            onClick={() => setStep((s) => Math.min(total - 1, s + 1))}
            disabled={step === total - 1}
          >
            Next
          </button>
        </div>

        <div className="cook__row cook__row--small">
          <button
            className={`cook__pill${muted ? " is-on" : ""}`}
            aria-pressed={muted}
            onClick={() => {
              stopTurn();
              setMuted((m) => !m);
            }}
          >
            {muted ? "Unmute" : "Mute"}
          </button>
          <button className="cook__pill cook__pill--stop" onClick={stopTurn}>
            Stop
          </button>
        </div>
      </nav>
    </main>
  );
}

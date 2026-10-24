import { useRef, useState } from "react";
import Kadhai from "../components/Kadhai.jsx";
import { LANGUAGES } from "../data/copy.js";
import { lineText, sayLine } from "../audio/voice.js";

const GREETINGS = ["hello_0", "hello_1", "hello_2"];
import "./Start.css";

// Flow A: pick a language and start. The "Start cooking" tap also unlocks browser audio later.
export default function Start({ language, setLanguage, lessTeasing, setLessTeasing, onStart, starting, notice }) {
  const [mood, setMood] = useState("intro");
  const [greeting, setGreeting] = useState(0);
  const timer = useRef(null);

  // Tapping the kadhai makes the seeds splutter and Amma ji says something else
  function poke() {
    const next = (greeting + 1) % GREETINGS.length;
    setGreeting(next);
    sayLine(GREETINGS[next], language).catch(() => {}); // the tap unlocks sound, so she can say it
    setMood("listening");
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setMood("idle"), 1100);
  }

  return (
    <main className="start">
      <div className="start__hero">
        <h1 className="start__brand">Amma ji</h1>

        <div className="start__hello">
          <button className="start__kadhai" onClick={poke} aria-label="Say hello to Amma ji">
            <Kadhai mood={mood} size={208} />
          </button>
          <p className="start__greeting" aria-live="polite">
            {lineText(GREETINGS[greeting], language)}
          </p>
        </div>
      </div>

      <div className="start__form">
        <fieldset className="start__languages">
          <legend>Which language should Amma ji speak?</legend>
          <div className="start__options">
            {LANGUAGES.map((lang) => (
              <label key={lang.id} className="start__option">
                <input
                  type="radio"
                  name="language"
                  value={lang.id}
                  checked={language === lang.id}
                  onChange={() => {
                    setLanguage(lang.id);
                    setGreeting(0);
                  }}
                />
                <span className="start__option-name">{lang.name}</span>
                <span className="start__option-hint">{lang.hint}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <label className="start__teasing">
          <input type="checkbox" checked={lessTeasing} onChange={(e) => setLessTeasing(e.target.checked)} />
          <span className="start__switch" aria-hidden="true" />
          <span>Less teasing, just the cooking</span>
        </label>

        <button className="start__go" onClick={onStart} disabled={starting}>
          {starting ? "Getting the kadhai ready" : "Start cooking"}
        </button>

        {notice && (
          <p className="start__notice" role="alert">
            {notice}
          </p>
        )}

        <p className="start__privacy">
          Amma ji only listens while you see "Mic on". What you say then is sent to Gnani to
          understand you. No recordings are saved.
        </p>
      </div>
    </main>
  );
}

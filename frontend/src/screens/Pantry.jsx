import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { unlockAudio } from "../audio/context.js";
import { startRecording } from "../audio/recorder.js";
import { canTalk, hush, lineText, sayLine, sayLive } from "../audio/voice.js";
import Kadhai from "../components/Kadhai.jsx";
import { heardLine } from "../data/copy.js";
import "./Pantry.css";

const TIMES = [null, 15, 30, 45];
// id, chip label, and the words that mean it when said out loud (English letters, Devanagari, Gurmukhi)
const ALLERGIES = [
  ["peanut", "Peanuts", /peanut|moongphal|mungphal|मूंगफली|मूँगफली|ਮੂੰਗਫਲੀ/i],
  ["nuts", "Nuts", /\bnuts?\b|kaju|badam|cashew|almond|काजू|बादाम|मेवा|ਕਾਜੂ|ਬਦਾਮ/i],
  ["dairy", "Milk", /milk|dairy|doodh|dudh|दूध|ਦੁੱਧ/i],
  ["gluten", "Wheat", /gluten|wheat|gehu|गेहूं|गेहूँ|ਕਣਕ/i],
  ["egg", "Egg", /\beggs?\b|\band[ae]\b|अंड|ਅੰਡ|ਆਂਡ/i],
  ["fish", "Fish", /fish|machh?li|मछली|ਮੱਛੀ/i],
  ["shellfish", "Prawns", /prawn|shrimp|jhinga|झींगा|ਝੀਂਗਾ/i],
  ["soy", "Soy", /\bsoy|soya|सोया|ਸੋਇਆ/i],
  ["sesame", "Til", /sesame|\btil\b|तिल|ਤਿਲ/i],
  ["mustard", "Mustard", /mustard|sarson|सरसों|ਸਰ੍ਹੋਂ|ਸਰੋਂ/i],
];
// "That's all" when listing, or "no" to the allergy question
const DONE_WORDS = /\b(bas|itna hi|that'?s all|that is all|nothing|nahi|nahin|nhi|no|none|done|ho gaya|dikhao|batao)\b|बस|इतना ही|नहीं|नही|हो गया|दिखाओ|ਬੱਸ|ਬਸ|ਨਹੀਂ|ਹੋ ਗਿਆ/i;
const STATUS = {
  idle: "Tap the kadhai and tell Amma ji what you have",
  speaking: "Amma ji is talking. Tap to stop her",
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
  const [amma, setAmma] = useState(""); // what Amma ji is saying, shown on screen too
  const [stage, setStage] = useState("have"); // have -> time -> allergy, then on to the dishes
  const recording = useRef(null);
  const talk = useRef(0); // every new turn (or a Stop) bumps this, so a cut-off turn goes quiet
  const said = useRef(0); // how many times she has reacted to ingredients
  const latest = useRef(pantry);
  latest.current = pantry;

  useEffect(() => {
    api.ingredients(language).then(setKnown, () => setKnown([]));
  }, [language]);

  // Amma ji starts the talk herself. After a page refresh there has been no tap, so she waits for one.
  useEffect(() => {
    if (canTalk()) turn("have", () => line("ask_have"));
    return quiet;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function quiet() {
    talk.current += 1;
    hush();
    recording.current?.stop();
    recording.current = null;
    setMood("idle");
  }

  const line = (name) => {
    setAmma(lineText(name, language));
    return sayLine(name, language);
  };
  const live = (text) => {
    setAmma(text);
    return sayLive(text, language);
  };

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
    return result;
  }

  // One take of the mic. Returns what was said, or null if nothing was.
  async function hearOnce(id) {
    setMood("listening");
    recording.current = await startRecording(unlockAudio());
    const wav = await recording.current.result;
    recording.current = null;
    if (!wav || id !== talk.current) return null;
    setMood("thinking");
    try {
      return (await api.hear(wav, language)).text;
    } catch (e) {
      if (e.status === 422) return null; // too short, or Gnani heard no words
      throw e;
    }
  }

  // One turn of the talk: Amma ji says something (or not, if the cook tapped first), listens, then acts on it
  async function turn(next, say = null, tries = 0) {
    const id = ++talk.current;
    setStage(next);
    setError("");
    try {
      if (say) {
        setMood("speaking");
        await say();
        if (id !== talk.current) return;
      }
      const text = await hearOnce(id);
      if (id !== talk.current) return;
      if (text === null) {
        if (tries < 1) return turn(next, () => line("not_heard"), tries + 1);
        setMood("idle");
        return setError("Amma ji did not hear anything. Tap the kadhai to talk, or use the buttons below.");
      }
      await ANSWERS[next](text, tries);
    } catch (e) {
      if (id !== talk.current) return;
      setMood("idle");
      setError(e.name === "NotAllowedError" ? "Amma ji needs the microphone. Allow it, or type below." : e.message);
    }
  }

  const ANSWERS = {
    async have(text, tries) {
      const result = await understand(text);
      if (result.have.length) {
        const first = said.current++ === 0;
        return turn("have", () => live(heardLine(result.have.map((i) => i.say), language, first)));
      }
      if (result.not_have.length) return turn("have"); // "paneer nahi hai": noted, keep listening
      if (DONE_WORDS.test(text) && latest.current.have.length) return afterIngredients();
      if (tries < 2) return turn("have", () => line(latest.current.have.length ? "not_heard" : "ask_have"), tries + 1);
      setMood("idle");
      setError("Amma ji did not catch any ingredients. Try saying them one by one, or type them below.");
    },
    async time(text) {
      await understand(text); // picks up "20 minute", "aadha ghanta", "jaldi", and any ingredient said too
      afterTime();
    },
    async allergy(text, tries) {
      const found = ALLERGIES.filter(([, , words]) => words.test(text)).map(([id]) => id);
      if (!found.length && !DONE_WORDS.test(text)) {
        // Not sure what they meant: ask again rather than guess there is no allergy
        if (tries < 1) return turn("allergy", () => line("not_heard"), tries + 1);
        setMood("idle");
        return setError("Tap anything Amma ji should keep out below, then Show me dishes.");
      }
      if (found.length) setPantry((p) => ({ ...p, allergies: [...new Set([...p.allergies, ...found])] }));
      finish();
    },
  };

  function afterIngredients() {
    if (latest.current.minutes == null) return turn("time", () => line("ask_time"));
    afterTime();
  }

  function afterTime() {
    if (!latest.current.allergies.length) return turn("allergy", () => line("ask_allergy"));
    finish();
  }

  async function finish() {
    const id = ++talk.current;
    setMood("speaking");
    await line("noted").catch(() => {});
    if (id === talk.current) onFind();
  }

  // The kadhai: stop her talking, finish a take early, or answer her current question
  function listen() {
    unlockAudio();
    if (mood === "listening") return recording.current?.stop();
    if (mood === "speaking") return quiet();
    if (mood !== "idle") return;
    turn(stage);
  }

  async function send(event) {
    event.preventDefault();
    if (!typed.trim()) return;
    quiet();
    setError("");
    setMood("thinking");
    try {
      const result = await understand(typed.trim());
      if (!result.have.length && !result.not_have.length) {
        setError("Amma ji did not catch any ingredients. Try them one by one, or pick from the list below.");
      }
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
        {amma && <p className="pantry__amma">{amma}</p>}
        <button className={`pantry__mic pantry__mic--${mood}`} onClick={listen} aria-label="Tell Amma ji what you have">
          <Kadhai mood={mood} size={128} />
        </button>
        <div>
          <p className="pantry__status" aria-live="polite">
            {STATUS[mood]}
          </p>
          {!amma && (
            <p className="pantry__example">Like: "Do aloo, paneer, pyaaz hai. 20 minute mein kuch bana do."</p>
          )}
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
        <button type="submit" disabled={!typed.trim() || mood === "thinking"}>
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

      <button className="big-button" onClick={() => (quiet(), onFind())} disabled={!pantry.have.length}>
        Show me dishes
      </button>
    </main>
  );
}

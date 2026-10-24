import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { unlockAudio } from "../audio/context.js";
import { playStream } from "../audio/player.js";
import { startRecording } from "../audio/recorder.js";
import Kadhai from "../components/Kadhai.jsx";
import { TIMER_DONE, WELCOME } from "../data/copy.js";
import "./Cooking.css";

const STATUS = {
  idle: "Tap the kadhai and talk to Amma ji",
  listening: "Listening. Tap again when you finish",
  thinking: "Amma ji is thinking",
  speaking: "Amma ji is speaking. Tap to stop her",
  muted: "Mic is off. Tap the kadhai to turn it on",
};
// Add ?dev to the address to see how long each part of a turn took
const DEV = new URLSearchParams(window.location.search).has("dev");

function clock(seconds) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

// Flow E: cooking mode. Tap the kadhai, speak, and Amma ji answers out loud.
export default function Cooking({ session, onExit, onEnded, onFinish }) {
  const [state, setState] = useState(session);
  const [syncedAt, setSyncedAt] = useState(() => Date.now());
  const [now, setNow] = useState(() => Date.now());
  const [mood, setMood] = useState("idle");
  const [muted, setMuted] = useState(false);
  const [chat, setChat] = useState({ you: null, amma: WELCOME[session.language] });
  const [error, setError] = useState("");
  const [typed, setTyped] = useState("");
  const [timing, setTiming] = useState(null);
  const turn = useRef(0); // every new turn (or Stop) bumps this, so stale answers are ignored
  const recording = useRef(null);
  const playing = useRef(null);
  const greeted = useRef(false);
  const announced = useRef(new Set());
  const language = state.language;

  function update(next) {
    setState(next);
    setSyncedAt(Date.now());
  }

  function fail(e, id) {
    if (id !== turn.current) return;
    setMood("idle");
    if (e.status === 404) return onEnded(e.message);
    if (e.name === "NotAllowedError") {
      return setError("Amma ji needs the microphone. Allow it in your browser settings, or type below.");
    }
    setError(e.message || "Something went wrong. Try again.");
  }

  // Say something out loud. Resolves when she finishes (or is stopped).
  async function speak(text, { speed = 1, id = turn.current, onStart } = {}) {
    const context = unlockAudio();
    const response = await api.speak(text, language, speed);
    if (id !== turn.current) return response.body?.cancel();
    const player = playStream(response, context, {
      onStart: () => {
        setMood("speaking");
        onStart?.();
      },
    });
    playing.current = player;
    await player.done;
    if (id === turn.current) {
      playing.current = null;
      setMood("idle");
    }
  }

  function stopAll() {
    turn.current += 1;
    recording.current?.stop();
    recording.current = null;
    playing.current?.stop();
    playing.current = null;
    setMood("idle");
  }

  async function answer(result, id, spokeAt) {
    update(result.state);
    setChat({ you: result.heard, amma: result.reply_text });
    const timings = { ...result.timing_ms };
    await speak(result.reply, {
      speed: result.effect?.tts_speed || 1,
      id,
      onStart: () => {
        timings.first_audio = Math.round(performance.now() - spokeAt);
        setTiming({ ...timings, warnings: result.warnings, by: result.answered_by });
      },
    });
    // "Ho gaya" on the last step: once she has answered, show what was made
    if (result.effect?.finished && id === turn.current) onFinish();
  }

  // The kadhai: start listening, finish early, or stop her talking
  async function talk() {
    const context = unlockAudio();
    if (muted) return setMuted(false);
    if (mood === "listening") return recording.current?.stop();
    if (mood !== "idle") return stopAll();
    const id = ++turn.current;
    setError("");
    try {
      setMood("listening");
      recording.current = await startRecording(context);
      const wav = await recording.current.result;
      recording.current = null;
      if (id !== turn.current) return;
      if (!wav) {
        setMood("idle");
        return setError("Amma ji did not hear anything. Tap the kadhai and speak a little closer.");
      }
      const spokeAt = performance.now();
      setMood("thinking");
      const result = await api.listen(state.session_id, wav);
      if (id !== turn.current) return;
      await answer(result, id, spokeAt);
    } catch (e) {
      fail(e, id);
    }
  }

  async function send(event) {
    event.preventDefault();
    const text = typed.trim();
    if (!text) return;
    stopAll();
    const id = turn.current;
    setTyped("");
    setError("");
    try {
      const sentAt = performance.now();
      setMood("thinking");
      const result = await api.say(state.session_id, text);
      if (id !== turn.current) return;
      await answer(result, id, sentAt);
    } catch (e) {
      fail(e, id);
    }
  }

  async function move(action) {
    stopAll();
    const id = turn.current;
    setError("");
    try {
      const next = await api.step(state.session_id, action);
      update(next);
      // Wait a moment before reading it out: three quick taps on Next make one voice request, not three
      await new Promise((r) => setTimeout(r, 450));
      if (id === turn.current) await speak(next.step.speak, { id });
    } catch (e) {
      fail(e, id);
    }
  }

  async function startStepTimer() {
    try {
      update(await api.timer(state.session_id, state.step.timer_min, `step ${state.step.n}`));
    } catch (e) {
      fail(e, turn.current);
    }
  }

  // Greet and read the first step once (the Start cooking tap already unlocked sound)
  useEffect(() => {
    if (greeted.current) return;
    greeted.current = true;
    speak(`${WELCOME[language]} ${state.step.speak}`).catch((e) => fail(e, turn.current));
  });

  // Tick once a second for the timers
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  // Keep the screen awake while cooking
  useEffect(() => {
    let lock = null;
    const ask = () => navigator.wakeLock?.request("screen").then((l) => (lock = l)).catch(() => {});
    const onShow = () => document.visibilityState === "visible" && ask();
    ask();
    document.addEventListener("visibilitychange", onShow);
    return () => {
      document.removeEventListener("visibilitychange", onShow);
      lock?.release().catch(() => {});
    };
  }, []);

  useEffect(() => () => stopAll(), []); // eslint-disable-line react-hooks/exhaustive-deps

  // Timers count down from the last time the server told us their seconds left
  const elapsed = Math.floor((now - syncedAt) / 1000);
  const timers = state.timers
    .map((t) => ({ ...t, left: Math.max(0, t.seconds_left - elapsed) }))
    .sort((a, b) => (a.left === 0) - (b.left === 0) || a.left - b.left);
  const timer = timers[0];

  // When a timer reaches zero, buzz and tell the cook (once per timer)
  useEffect(() => {
    timers
      .filter((t) => t.left === 0 && !announced.current.has(t.ends_at))
      .forEach((t) => {
        announced.current.add(t.ends_at);
        navigator.vibrate?.([300, 150, 300]);
        if (mood === "idle") speak(TIMER_DONE[language](t.label)).catch(() => {});
      });
  });

  const shown = muted ? "muted" : mood;
  const step = state.step;

  return (
    <main className="cook">
      <header className="cook__top">
        <button className="cook__back" onClick={onExit} aria-label="Leave cooking mode">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M15 5l-7 7 7 7" />
          </svg>
        </button>
        <div className="cook__title">
          <h1>{state.recipe_name}</h1>
          <p>
            Step {step.n} of {state.total_steps}
          </p>
        </div>
        {mood === "listening" && <span className="cook__mic-on">Mic on</span>}
      </header>

      <ol className="cook__progress" aria-hidden="true">
        {Array.from({ length: state.total_steps }, (_, i) => (
          <li key={i} className={i + 1 < step.n ? "is-done" : i + 1 === step.n ? "is-now" : ""} />
        ))}
      </ol>

      <section className="cook__step" aria-live="polite">
        <p className="cook__step-text" key={step.n}>
          {step.text}
        </p>
        {step.safety && (
          <p className="cook__safety">
            <strong>Careful: </strong>
            {step.safety}
          </p>
        )}
      </section>

      {timer ? (
        <section className={`cook__timer${timer.left === 0 ? " is-done" : ""}`} aria-label="Timer">
          <span className="cook__timer-label">{timer.left === 0 ? `${timer.label} is done` : timer.label}</span>
          <span className="cook__timer-time">{clock(timer.left)}</span>
          <span
            className="cook__timer-bar"
            style={{ "--left": timer.minutes ? timer.left / (timer.minutes * 60) : 1 }}
            aria-hidden="true"
          />
        </section>
      ) : (
        step.timer_min && (
          <button className="cook__timer-start" onClick={startStepTimer}>
            Start a {step.timer_min} minute timer
          </button>
        )
      )}

      <section className="cook__chat" aria-label="Last thing you said and her answer">
        {chat.you && <p className="cook__you">{chat.you}</p>}
        <p className="cook__amma">{chat.amma}</p>
        {error && (
          <p className="cook__error" role="alert">
            {error}
          </p>
        )}
      </section>

      <form className="cook__type" onSubmit={send}>
        <label className="visually-hidden" htmlFor="type-to-amma">
          Type to Amma ji
        </label>
        <input
          id="type-to-amma"
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          placeholder="Or type to Amma ji"
          autoComplete="off"
          enterKeyHint="send"
        />
        <button type="submit" disabled={!typed.trim()}>
          Send
        </button>
      </form>

      {DEV && timing && (
        <p className="cook__dev">
          STT {timing.stt ?? "-"} ms, {timing.by === "code" ? "answered in code" : `Groq ${timing.groq} ms`}, first
          sound {timing.first_audio} ms after you stopped
          {timing.warnings?.length ? `. Check: ${timing.warnings.join(", ")}` : ""}
        </p>
      )}

      <p className="cook__note">Keep this screen open while cooking</p>

      <nav className="cook__dock" aria-label="Cooking controls">
        <p className="cook__status" aria-live="polite">
          {STATUS[shown]}
        </p>

        <div className="cook__row">
          <button className="cook__nav" onClick={() => move("previous")} disabled={step.n === 1}>
            Back
          </button>

          <button
            className={`cook__mic cook__mic--${shown}`}
            onClick={talk}
            aria-label={
              muted ? "Turn the mic on" : mood === "idle" ? "Talk to Amma ji" : mood === "listening" ? "Done talking" : "Stop"
            }
          >
            <Kadhai mood={shown} size={116} />
          </button>

          {step.n === state.total_steps ? (
            <button
              className="cook__nav cook__nav--done"
              onClick={() => {
                stopAll();
                onFinish();
              }}
            >
              Done
            </button>
          ) : (
            <button className="cook__nav" onClick={() => move("next")}>
              Next
            </button>
          )}
        </div>

        <div className="cook__row cook__row--small">
          <button
            className={`cook__pill${muted ? " is-on" : ""}`}
            aria-pressed={muted}
            onClick={() => {
              stopAll();
              setMuted((m) => !m);
            }}
          >
            {muted ? "Unmute" : "Mute"}
          </button>
          <button className="cook__pill cook__pill--stop" onClick={stopAll}>
            Stop
          </button>
        </div>
      </nav>
    </main>
  );
}

import { useEffect, useState } from "react";
import { api } from "./api.js";
import { unlockAudio } from "./audio/context.js";
import Cooking from "./screens/Cooking.jsx";
import Start from "./screens/Start.jsx";

// Small helpers for browser storage. The app still works if storage is blocked.
function read(store, key, fallback) {
  try {
    const v = store.getItem(key);
    return v === null ? fallback : JSON.parse(v);
  } catch {
    return fallback;
  }
}

function write(store, key, value) {
  try {
    if (value === null) store.removeItem(key);
    else store.setItem(key, JSON.stringify(value));
  } catch {
    // storage blocked: nothing to do
  }
}

const onCookingPage = () => window.location.hash === "#cooking";

export default function App() {
  const [language, setLanguage] = useState(() => read(localStorage, "language", "hi-en"));
  const [lessTeasing, setLessTeasing] = useState(() => read(localStorage, "lessTeasing", false));
  const [session, setSession] = useState(null);
  const [starting, setStarting] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => write(localStorage, "language", language), [language]);
  useEffect(() => write(localStorage, "lessTeasing", lessTeasing), [lessTeasing]);
  useEffect(() => {
    document.documentElement.lang = language === "hi-en" ? "hi-Latn" : language;
  }, [language]);

  function backToStart(message = "") {
    write(sessionStorage, "session", null);
    setSession(null);
    setNotice(message);
    if (onCookingPage()) window.location.hash = "";
  }

  // Coming back to #cooking after a refresh: pick the session up again if the server still has it
  useEffect(() => {
    const id = read(sessionStorage, "session", null);
    if (!onCookingPage() || !id) return backToStart();
    api.get(id).then(setSession, () => backToStart("That cooking session ended. Start a new one."));
    const onHash = () => !onCookingPage() && setSession(null);
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function start() {
    unlockAudio(); // this tap is what lets the browser play Amma ji's voice
    setStarting(true);
    setNotice("");
    try {
      const fresh = await api.start({ recipe_id: "dal_tadka", language, teasing: !lessTeasing });
      write(sessionStorage, "session", fresh.session_id);
      setSession(fresh);
      window.location.hash = "cooking";
    } catch (e) {
      setNotice(e.message);
    } finally {
      setStarting(false);
    }
  }

  if (session && onCookingPage()) {
    return <Cooking key={session.session_id} session={session} onExit={() => backToStart()} onEnded={backToStart} />;
  }
  return (
    <Start
      language={language}
      setLanguage={setLanguage}
      lessTeasing={lessTeasing}
      setLessTeasing={setLessTeasing}
      onStart={start}
      starting={starting}
      notice={notice}
    />
  );
}

import { useEffect, useState } from "react";
import { api } from "./api.js";
import { unlockAudio } from "./audio/context.js";
import Cooking from "./screens/Cooking.jsx";
import Dish from "./screens/Dish.jsx";
import Dishes from "./screens/Dishes.jsx";
import Finish from "./screens/Finish.jsx";
import Pantry from "./screens/Pantry.jsx";
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

const EMPTY_PANTRY = { have: [], notHave: [], minutes: null, veg: false, allergies: [] };

// Which screen to show comes from the address: #pantry, #dishes, #dish/ID, #cooking, #done, or the start screen
function route() {
  const [screen, id] = window.location.hash.replace(/^#/, "").split("/");
  return { screen: screen || "start", id };
}

function go(hash) {
  window.location.hash = hash;
}

export default function App() {
  const [where, setWhere] = useState(route);
  const [language, setLanguage] = useState(() => read(localStorage, "language", "hi-en"));
  const [lessTeasing, setLessTeasing] = useState(() => read(localStorage, "lessTeasing", false));
  const [pantry, setPantry] = useState(() => read(sessionStorage, "pantry", EMPTY_PANTRY));
  const [session, setSession] = useState(null);
  const [summary, setSummary] = useState(() => read(sessionStorage, "summary", null));
  const [starting, setStarting] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => write(localStorage, "language", language), [language]);
  useEffect(() => write(localStorage, "lessTeasing", lessTeasing), [lessTeasing]);
  useEffect(() => write(sessionStorage, "pantry", pantry), [pantry]);
  useEffect(() => write(sessionStorage, "summary", summary), [summary]);
  useEffect(() => {
    document.documentElement.lang = language === "hi-en" ? "hi-Latn" : language;
  }, [language]);

  useEffect(() => {
    const onHash = () => setWhere(route());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // Coming back to #cooking after a refresh: pick the session up again if the server still has it
  useEffect(() => {
    if (where.screen !== "cooking" || session) return;
    const id = read(sessionStorage, "session", null);
    if (!id) return go("");
    api.get(id).then(setSession, () => {
      setNotice("That cooking session ended. Start a new one.");
      go("");
    });
  }, [where.screen]); // eslint-disable-line react-hooks/exhaustive-deps

  function ended(message = "") {
    write(sessionStorage, "session", null);
    setSession(null);
    setNotice(message);
    go("dishes");
  }

  // The dish is ready: get the summary, then the cooking session is over
  async function finished() {
    try {
      setSummary(await api.finish(session.session_id));
      go("done");
    } catch (e) {
      ended(e.message);
    }
  }

  async function cook(recipeId) {
    unlockAudio(); // this tap is what lets the browser play Amma ji's voice
    setStarting(true);
    try {
      const fresh = await api.start({
        recipe_id: recipeId,
        language,
        teasing: !lessTeasing,
        allergies: pantry.allergies,
      });
      write(sessionStorage, "session", fresh.session_id);
      setSession(fresh);
      go("cooking");
    } catch (e) {
      setNotice(e.message);
    } finally {
      setStarting(false);
    }
  }

  if (where.screen === "cooking" && session) {
    return (
      <Cooking
        key={session.session_id}
        session={session}
        onExit={() => ended()}
        onEnded={ended}
        onFinish={finished}
      />
    );
  }
  if (where.screen === "done" && summary) {
    return (
      <Finish
        key={summary.dish_id}
        summary={summary}
        sessionId={session?.session_id ?? read(sessionStorage, "session", null)}
        onAgain={() => go("pantry")}
        onHome={() => go("")}
      />
    );
  }
  if (where.screen === "pantry") {
    return (
      <Pantry language={language} pantry={pantry} setPantry={setPantry} onFind={() => go("dishes")} onBack={() => go("")} />
    );
  }
  if (where.screen === "dishes") {
    return <Dishes language={language} pantry={pantry} onOpen={(id) => go(`dish/${id}`)} onBack={() => go("pantry")} />;
  }
  if (where.screen === "dish" && where.id) {
    return (
      <Dish id={where.id} language={language} onCook={cook} onBack={() => go("dishes")} starting={starting} />
    );
  }
  return (
    <Start
      language={language}
      setLanguage={setLanguage}
      lessTeasing={lessTeasing}
      setLessTeasing={setLessTeasing}
      onStart={() => {
        unlockAudio();
        setNotice("");
        go("pantry");
      }}
      starting={false}
      notice={notice}
    />
  );
}

import { useEffect, useState } from "react";
import Cooking from "./screens/Cooking.jsx";
import Start from "./screens/Start.jsx";

// Remembered on this device only, for convenience. Works fine if storage is blocked.
function remembered(key, fallback) {
  try {
    const v = localStorage.getItem(key);
    return v === null ? fallback : JSON.parse(v);
  } catch {
    return fallback;
  }
}

function remember(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // storage blocked: nothing to do
  }
}

// Which screen to show comes from the address bar: #cooking or the start screen
function screenFromHash() {
  return window.location.hash === "#cooking" ? "cooking" : "start";
}

export default function App() {
  const [screen, setScreen] = useState(screenFromHash);
  const [language, setLanguage] = useState(() => remembered("language", "hi-en"));
  const [lessTeasing, setLessTeasing] = useState(() => remembered("lessTeasing", false));

  useEffect(() => {
    const onHash = () => setScreen(screenFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => remember("language", language), [language]);
  useEffect(() => remember("lessTeasing", lessTeasing), [lessTeasing]);

  useEffect(() => {
    document.documentElement.lang = language === "hi-en" ? "hi-Latn" : language;
  }, [language]);

  if (screen === "cooking") {
    return <Cooking language={language} onExit={() => (window.location.hash = "")} />;
  }
  return (
    <Start
      language={language}
      setLanguage={setLanguage}
      lessTeasing={lessTeasing}
      setLessTeasing={setLessTeasing}
      onStart={() => (window.location.hash = "cooking")}
    />
  );
}

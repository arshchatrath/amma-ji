// Amma ji talking outside cooking mode. Fixed lines play from files made once with Timbre
// (backend/scripts/make_voice_lines.py), so they start at once and cost nothing. Lines that depend on
// what the cook said go to Timbre live. Only one line plays at a time: a new one cuts off the old.
import { api } from "../api.js";
import LINES from "../data/lines.json";
import { unlockAudio } from "./context.js";
import { playStream } from "./player.js";

let current = null;
let token = 0;

export function hush() {
  token += 1;
  current?.stop();
  current = null;
}

// Browsers only play sound after a tap. After a page refresh there has been none, so stay quiet.
export const canTalk = () => unlockAudio().state === "running";

const untagged = (text) => text.replace(/<[^>]+>\s*/g, "").trim();

// What the screen shows for a fixed line: English letters for Hinglish, no audio tags
export function lineText(name, language) {
  const line = LINES[name][language];
  return line.show || untagged(line.say);
}

// Speak live with Timbre. Resolves when she finishes, or is cut off.
export async function sayLive(text, language) {
  hush();
  const mine = token;
  const response = await api.speak(text, language);
  if (mine !== token) return response.body?.cancel();
  const player = playStream(response, unlockAudio());
  current = player;
  await player.done;
}

// A fixed line from its file. Falls back to live Timbre if the file is not made yet.
export async function sayLine(name, language) {
  hush();
  const mine = token;
  const context = unlockAudio();
  const res = await fetch(`${import.meta.env.BASE_URL}voice/${language}/${name}.mp3`).catch(() => null);
  // A missing file can come back as the app's own page, so check it really is audio
  if (!res?.ok || !res.headers.get("content-type")?.startsWith("audio")) {
    return sayLive(LINES[name][language].say, language);
  }
  const buffer = await context.decodeAudioData(await res.arrayBuffer());
  if (mine !== token) return;
  const source = context.createBufferSource();
  source.buffer = buffer;
  source.connect(context.destination);
  let end;
  const done = new Promise((resolve) => (end = resolve));
  source.onended = end;
  current = {
    stop() {
      try {
        source.stop();
      } catch {
        // already finished
      }
      end();
    },
  };
  source.start();
  await done;
}

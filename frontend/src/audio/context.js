// One AudioContext for the whole app. Browsers only allow sound after a tap, so the
// "Start cooking" tap calls unlockAudio() and every later tap keeps it awake.
let context = null;

export function unlockAudio() {
  if (!context) context = new AudioContext();
  if (context.state === "suspended") context.resume();
  return context;
}

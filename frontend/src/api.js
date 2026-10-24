// How the screens talk to Amma ji's server. In development, Vite forwards /api to
// localhost:8010 (see vite.config.js). In production, VITE_API_URL points at the server.
const BASE = import.meta.env.VITE_API_URL || "";

async function call(path, options = {}) {
  let res;
  try {
    res = await fetch(BASE + path, options);
  } catch (e) {
    if (e.name === "AbortError") throw e;
    throw new Error("Can't reach Amma ji's server. Check your internet and try again.");
  }
  if (!res.ok) {
    let detail = `Something went wrong (${res.status}). Try again.`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // not JSON: keep the plain message
    }
    const error = new Error(detail);
    error.status = res.status;
    throw error;
  }
  return res;
}

const post = (body) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  start: (options) => call("/api/sessions", post(options)).then((r) => r.json()),
  get: (id) => call(`/api/sessions/${id}`).then((r) => r.json()),
  step: (id, action) => call(`/api/sessions/${id}/step`, post({ action })).then((r) => r.json()),
  timer: (id, minutes, label) => call(`/api/sessions/${id}/timer`, post({ minutes, label })).then((r) => r.json()),
  finish: (id) => call(`/api/sessions/${id}/finish`, post({})).then((r) => r.json()),
  feedback: (id, rating) => call(`/api/sessions/${id}/feedback`, post({ rating })).then((r) => r.json()),
  say: (id, text) => call(`/api/sessions/${id}/say`, post({ text })).then((r) => r.json()),
  listen: (id, wav) =>
    call(`/api/sessions/${id}/listen`, { method: "POST", headers: { "Content-Type": "audio/wav" }, body: wav }).then(
      (r) => r.json(),
    ),
  speak: (text, language, speed = 1, signal) => call("/api/speak", { ...post({ text, language, speed }), signal }),
  hear: (wav, language) =>
    call(`/api/hear?language=${language}`, { method: "POST", headers: { "Content-Type": "audio/wav" }, body: wav }).then(
      (r) => r.json(),
    ),
  pantry: (text, language) => call("/api/pantry", post({ text, language })).then((r) => r.json()),
  pick: (text, options) => call("/api/pick", post({ text, options })).then((r) => r.json()),
  suggest: (options) => call("/api/suggest", post(options)).then((r) => r.json()),
  recipe: (id, language) => call(`/api/recipes/${id}?language=${language}`).then((r) => r.json()),
  recipes: (language) => call(`/api/recipes?language=${language}`).then((r) => r.json()),
  ingredients: (language) => call(`/api/ingredients?language=${language}`).then((r) => r.json()),
};

// Words the app shows or says before the server answers. Dish data comes from the server.

export const LANGUAGES = [
  { id: "hi-en", name: "Hinglish", hint: "Jaise hum ghar pe bolte hain" },
  { id: "hi", name: "हिंदी", hint: "Hindi" },
  { id: "pa", name: "ਪੰਜਾਬੀ", hint: "Punjabi" },
  { id: "en", name: "English", hint: "Simple Indian English" },
];

// Fixed lines Amma ji speaks (greetings, questions) are in lines.json, with a sound file for each.
// The ones below are put together from what the cook said, so Timbre speaks them live.

// Names joined the way people say them: आलू, पनीर और प्याज़
function join(names, and) {
  return names.length < 2 ? names.join("") : `${names.slice(0, -1).join(", ")} ${and} ${names.at(-1)}`;
}
const pickOne = (list) => list[Math.floor(Math.random() * list.length)];

// After the cook names a few things. The first time she says how to finish ("bas").
const HEARD = {
  hi: [(l) => `अच्छा, ${l}। और कुछ? हो गया तो बोलो बस।`, (l) => `वाह, ${l}! और क्या क्या है बेटा?`, (l) => `${l}, बढ़िया। कुछ और?`],
  pa: [(l) => `ਅੱਛਾ, ${l}। ਹੋਰ ਕੁਝ? ਹੋ ਗਿਆ ਤਾਂ ਬੋਲੋ ਬੱਸ।`, (l) => `ਵਾਹ, ${l}! ਹੋਰ ਕੀ ਕੀ ਹੈ ਬੇਟਾ?`, (l) => `${l}, ਵਧੀਆ। ਹੋਰ ਕੁਝ?`],
  en: [(l) => `Okay, ${l}. Anything else? If that's all, say bas.`, (l) => `Wah, ${l}! What else, बेटा?`, (l) => `${l}, lovely. Anything more?`],
};
const AND = { hi: "और", pa: "ਤੇ", en: "and" };
const speech = (language) => (language === "hi-en" ? "hi" : language); // Hinglish is spoken in Devanagari

export function heardLine(names, language, first) {
  const lang = speech(language);
  const line = first ? HEARD[lang][0] : pickOne(HEARD[lang]);
  return line(join(names, AND[lang]));
}

// Reading out the top dishes, then asking which one
const DISHES = {
  hi: (a, rest) => `मेरे हिसाब से ${a} सबसे बढ़िया रहेगा।${rest ? ` या फिर ${rest}।` : ""} बोलो, कौन सा बनाएँ?`,
  pa: (a, rest) => `ਮੇਰੇ ਹਿਸਾਬ ਨਾਲ ${a} ਸਭ ਤੋਂ ਵਧੀਆ ਰਹੇਗਾ।${rest ? ` ਜਾਂ ਫਿਰ ${rest}।` : ""} ਦੱਸੋ, ਕਿਹੜਾ ਬਣਾਈਏ?`,
  en: (a, rest) => `I think ${a} is the best one.${rest ? ` Or ${rest}.` : ""} Tell me, which one, बेटा?`,
};
const OR = { hi: "या", pa: "ਜਾਂ", en: "or" };

export function dishesLine(names, language) {
  const lang = speech(language);
  return DISHES[lang](names[0], join(names.slice(1, 3), OR[lang]));
}

// Amma ji's first line in cooking mode, before she reads step 1
export const WELCOME = {
  "hi-en": "चल बेटा, शुरू करते हैं।",
  hi: "चल बेटा, शुरू करते हैं।",
  pa: "ਚੱਲ ਬੇਟਾ, ਸ਼ੁਰੂ ਕਰਦੇ ਹਾਂ।",
  en: "Come, बेटा, let's start.",
};

// What Amma ji says when a timer reaches zero
export const TIMER_DONE = {
  "hi-en": (label) => `बेटा, ${label} का टाइमर पूरा हो गया।`,
  hi: (label) => `बेटा, ${label} का टाइमर पूरा हो गया।`,
  pa: (label) => `ਬੇਟਾ, ${label} ਦਾ ਟਾਈਮਰ ਪੂਰਾ ਹੋ ਗਿਆ।`,
  en: (label) => `बेटा, the ${label} timer is done.`,
};

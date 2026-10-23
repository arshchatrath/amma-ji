// Words the app shows or says before the server answers. Dish data comes from the server.

export const LANGUAGES = [
  { id: "hi-en", name: "Hinglish", hint: "Jaise hum ghar pe bolte hain" },
  { id: "hi", name: "हिंदी", hint: "Hindi" },
  { id: "pa", name: "ਪੰਜਾਬੀ", hint: "Punjabi" },
  { id: "en", name: "English", hint: "Simple Indian English" },
];

export const GREETINGS = {
  "hi-en": ["Aaja beta, aaj kya banayein?", "Bhookh lagi hai? Chal, kitchen mein milte hain.", "Masale tayyar hain. Tu tayyar hai?"],
  hi: ["आजा बेटा, आज क्या बनाएँ?", "भूख लगी है? चल, किचन में मिलते हैं।", "मसाले तैयार हैं। तू तैयार है?"],
  pa: ["ਆਜਾ ਬੇਟਾ, ਅੱਜ ਕੀ ਬਣਾਈਏ?", "ਭੁੱਖ ਲੱਗੀ ਹੈ? ਚੱਲ, ਰਸੋਈ ਵਿੱਚ ਮਿਲਦੇ ਹਾਂ।", "ਮਸਾਲੇ ਤਿਆਰ ਨੇ। ਤੂੰ ਤਿਆਰ ਹੈਂ?"],
  en: ["Come, beta. What are we making today?", "Hungry? Meet me in the kitchen.", "The masalas are ready. Are you?"],
};

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

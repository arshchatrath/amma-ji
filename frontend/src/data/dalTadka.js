// Pretend data so the screens can be designed before the backend is connected.
// Same dal tadka as backend/day1/brain.py. Steps written in our own words.

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

export const RECIPE = {
  name: { "hi-en": "Dal tadka", hi: "दाल तड़का", pa: "ਦਾਲ ਤੜਕਾ", en: "Dal tadka" },
  steps: [
    {
      "hi-en": "Toor dal ko 2-3 baar dho lo, jab tak paani saaf na ho jaaye.",
      hi: "तूर दाल को 2-3 बार धो लो, जब तक पानी साफ़ न हो जाए।",
      pa: "ਤੂਰ ਦਾਲ ਨੂੰ 2-3 ਵਾਰ ਧੋ ਲਓ, ਜਦੋਂ ਤੱਕ ਪਾਣੀ ਸਾਫ਼ ਨਾ ਹੋ ਜਾਵੇ।",
      en: "Wash the toor dal 2 or 3 times, until the water runs clear.",
    },
    {
      "hi-en": "Dal ko cooker mein daalo, saath mein 2 cup paani, haldi aur namak.",
      hi: "दाल को कुकर में डालो, साथ में 2 कप पानी, हल्दी और नमक।",
      pa: "ਦਾਲ ਨੂੰ ਕੁੱਕਰ ਵਿੱਚ ਪਾਓ, ਨਾਲ 2 ਕੱਪ ਪਾਣੀ, ਹਲਦੀ ਅਤੇ ਲੂਣ।",
      en: "Put the dal in the cooker with 2 cups water, turmeric and salt.",
    },
    {
      "hi-en": "Medium aanch pe 3 seeti tak pakao, lagbhag 15 minute.",
      hi: "मध्यम आँच पर 3 सीटी तक पकाओ, लगभग 15 मिनट।",
      pa: "ਦਰਮਿਆਨੀ ਅੱਗ ਤੇ 3 ਸੀਟੀਆਂ ਤੱਕ ਪਕਾਓ, ਲਗਭਗ 15 ਮਿੰਟ।",
      en: "Pressure cook on medium heat for 3 whistles, about 15 minutes.",
      safety: {
        "hi-en": "Cooker kholne se pehle saari bhaap nikal jaane do.",
        hi: "कुकर खोलने से पहले सारी भाप निकल जाने दो।",
        pa: "ਕੁੱਕਰ ਖੋਲ੍ਹਣ ਤੋਂ ਪਹਿਲਾਂ ਸਾਰੀ ਭਾਫ਼ ਨਿਕਲ ਜਾਣ ਦਿਓ।",
        en: "Let the pressure go down fully before you open the cooker.",
      },
    },
    {
      "hi-en": "Cooker kholo, dal ko halka sa mash karo aur 5 minute dheemi aanch pe pakne do.",
      hi: "कुकर खोलो, दाल को हल्का सा मैश करो और 5 मिनट धीमी आँच पर पकने दो।",
      pa: "ਕੁੱਕਰ ਖੋਲ੍ਹੋ, ਦਾਲ ਨੂੰ ਹਲਕਾ ਜਿਹਾ ਮੈਸ਼ ਕਰੋ ਅਤੇ 5 ਮਿੰਟ ਹੌਲੀ ਅੱਗ ਤੇ ਪੱਕਣ ਦਿਓ।",
      en: "Open the cooker, mash the dal lightly and let it simmer for 5 minutes.",
    },
    {
      "hi-en": "Chhoti kadhai mein ghee garam karo. Jeera daalo, chatakne lage to pyaaz aur lehsun. Sunehra hone tak bhuno.",
      hi: "छोटी कड़ाही में घी गरम करो। जीरा डालो, चटकने लगे तो प्याज़ और लहसुन। सुनहरा होने तक भूनो।",
      pa: "ਛੋਟੀ ਕੜਾਹੀ ਵਿੱਚ ਘਿਓ ਗਰਮ ਕਰੋ। ਜੀਰਾ ਪਾਓ, ਤਿੜਕਣ ਲੱਗੇ ਤਾਂ ਪਿਆਜ਼ ਅਤੇ ਲਸਣ। ਸੁਨਹਿਰੀ ਹੋਣ ਤੱਕ ਭੁੰਨੋ।",
      en: "Heat ghee in a small pan. Add cumin, and when it crackles add onion and garlic. Cook till golden.",
    },
    {
      "hi-en": "Tamatar aur laal mirch daalo. Tamatar naram hone tak pakao.",
      hi: "टमाटर और लाल मिर्च डालो। टमाटर नरम होने तक पकाओ।",
      pa: "ਟਮਾਟਰ ਅਤੇ ਲਾਲ ਮਿਰਚ ਪਾਓ। ਟਮਾਟਰ ਨਰਮ ਹੋਣ ਤੱਕ ਪਕਾਓ।",
      en: "Add tomato and red chilli powder. Cook till the tomato turns soft.",
    },
    {
      "hi-en": "Tadka dal mein daalo, garam masala daalo aur 2 minute pakao. Ho gaya!",
      hi: "तड़का दाल में डालो, गरम मसाला डालो और 2 मिनट पकाओ। हो गया!",
      pa: "ਤੜਕਾ ਦਾਲ ਵਿੱਚ ਪਾਓ, ਗਰਮ ਮਸਾਲਾ ਪਾਓ ਅਤੇ 2 ਮਿੰਟ ਪਕਾਓ। ਬਣ ਗਈ!",
      en: "Pour the tadka into the dal, add garam masala and simmer 2 minutes. Done!",
    },
  ],
};

// The wow moment from the brief, and one more exchange the mic demo plays
export const EXCHANGES = [
  {
    you: {
      "hi-en": "Amma ji, maine paani zyada daal diya.",
      hi: "अम्मा जी, मैंने पानी ज़्यादा डाल दिया।",
      pa: "ਅੰਮਾ ਜੀ, ਮੈਂ ਪਾਣੀ ਜ਼ਿਆਦਾ ਪਾ ਦਿੱਤਾ।",
      en: "Amma ji, I added too much water.",
    },
    amma: {
      "hi-en": "Koi baat nahi beta. Dhakkan hata ke 5 minute tez aanch pe pakne do, paani sookh jayega.",
      hi: "कोई बात नहीं बेटा। ढक्कन हटा के 5 मिनट तेज़ आँच पे पकने दो, पानी सूख जाएगा।",
      pa: "ਕੋਈ ਗੱਲ ਨਹੀਂ ਬੇਟਾ। ਢੱਕਣ ਹਟਾ ਕੇ 5 ਮਿੰਟ ਤੇਜ਼ ਅੱਗ ਤੇ ਪੱਕਣ ਦਿਓ, ਪਾਣੀ ਸੁੱਕ ਜਾਵੇਗਾ।",
      en: "No problem, beta. Take the lid off and boil on high for 5 minutes. The extra water will dry up.",
    },
  },
  {
    you: {
      "hi-en": "Timer mein kitna time bacha hai?",
      hi: "टाइमर में कितना टाइम बचा है?",
      pa: "ਟਾਈਮਰ ਵਿੱਚ ਕਿੰਨਾ ਸਮਾਂ ਬਚਿਆ ਹੈ?",
      en: "How much time is left on the timer?",
    },
    amma: {
      "hi-en": "Bas thoda sa aur beta. Tab tak tadka ki taiyari kar lo, pyaaz kaat lo.",
      hi: "बस थोड़ा सा और बेटा। तब तक तड़के की तैयारी कर लो, प्याज़ काट लो।",
      pa: "ਬੱਸ ਥੋੜ੍ਹਾ ਜਿਹਾ ਹੋਰ ਬੇਟਾ। ਤਦ ਤੱਕ ਤੜਕੇ ਦੀ ਤਿਆਰੀ ਕਰ ਲਓ, ਪਿਆਜ਼ ਕੱਟ ਲਓ।",
      en: "Just a little longer, beta. Get the tadka ready meanwhile, chop the onion.",
    },
  },
];

"""Simple commands answered in code, with no Groq call: next, back, repeat, slower, how much time left.

Only a whole sentence that is just the command counts. "Ho gaya" moves on, but "namak zyada ho
gaya" is a mistake, so it still goes to Groq. Saves Groq's daily limit and about a second a turn.
"""
import re

from .brain import timer_reply
from .session import RECIPES, apply_tool, step_text

# Words people put around a command that do not change it
FILLER = {
    "amma", "ammaji", "ji", "please", "plz", "pls", "zara", "jara", "ok", "okay", "accha", "acha", "achha",
    "haan", "han", "chalo", "toh", "to", "ab", "hai", "beta", "now", "so", "then",
    "अम्मा", "अम्माजी", "जी", "जरा", "ओके", "अच्छा", "हाँ", "हां", "चलो", "तो", "अब", "है", "प्लीज",
    "ਅੰਮਾ", "ਅੰਮਾਜੀ", "ਜੀ", "ਜ਼ਰਾ", "ਜਰਾ", "ਓਕੇ", "ਅੱਛਾ", "ਹਾਂ", "ਚੱਲੋ", "ਤਾਂ", "ਹੁਣ", "ਹੈ",
}

COMMANDS = {
    "next": [
        "next", "next step", "done", "what next", "whats next", "go on", "continue", "move on", "next one",
        "agla", "agla step", "agla step batao", "agla step bolo", "aage", "aage badho", "aage chalo",
        "ho gaya", "hogaya", "ho gya", "kya karna hai", "kya karu", "kya karun", "kya karoon", "phir kya",
        "अगला", "अगला स्टेप", "अगला स्टैप", "अगला स्टेप बताओ", "अगला स्टेप बोलो", "आगे", "आगे बढ़ो", "आगे चलो",
        "हो गया", "क्या करना", "क्या करना है", "क्या करूँ", "क्या करूं", "क्या करें", "फिर क्या", "नेक्स्ट", "नेक्स्ट स्टेप",
        "ਅਗਲਾ", "ਅਗਲਾ ਸਟੈਪ", "ਅਗਲਾ ਸਟੈੱਪ", "ਅਗਲਾ ਸਟੈਪ ਦੱਸੋ", "ਅੱਗੇ", "ਅੱਗੇ ਚੱਲੋ", "ਹੋ ਗਿਆ", "ਕੀ ਕਰਨਾ",
        "ਕੀ ਕਰਨਾ ਹੈ", "ਕੀ ਕਰਾਂ", "ਫਿਰ ਕੀ", "ਨੈਕਸਟ",
    ],
    "previous": [
        "back", "go back", "previous", "previous step", "last step", "step before",
        "pichla", "pichla step", "pichla step batao", "peeche", "peeche jao", "wapas", "wapas jao",
        "पिछला", "पिछला स्टेप", "पिछला स्टैप", "पिछला स्टेप बताओ", "पीछे", "पीछे जाओ", "वापस", "वापस जाओ",
        "ਪਿਛਲਾ", "ਪਿਛਲਾ ਸਟੈਪ", "ਪਿਛਲਾ ਸਟੈੱਪ", "ਪਿੱਛੇ", "ਪਿੱਛੇ ਜਾਓ", "ਵਾਪਸ",
    ],
    "repeat": [
        "repeat", "repeat that", "say again", "say that again", "again", "what did you say", "pardon",
        "phir se", "phir se bolo", "fir se", "fir se bolo", "dobara", "dobara bolo", "repeat karo",
        "kya bola", "kya kaha", "samjha nahi", "samajh nahi aaya", "ek baar aur",
        "फिर से", "फिर से बोलो", "फिर से बताओ", "दोबारा", "दोबारा बोलो", "रिपीट", "रिपीट करो", "क्या बोला",
        "क्या कहा", "समझा नहीं", "समझ नहीं आया", "एक बार और",
        "ਫਿਰ ਤੋਂ", "ਫਿਰ ਤੋਂ ਦੱਸੋ", "ਦੁਬਾਰਾ", "ਦੁਬਾਰਾ ਦੱਸੋ", "ਕੀ ਕਿਹਾ", "ਸਮਝ ਨਹੀਂ ਆਇਆ", "ਇੱਕ ਵਾਰ ਹੋਰ",
    ],
    "slow": [
        "slowly", "slower", "say it slowly", "speak slowly", "slow",
        "dheere", "dheere bolo", "dheere se bolo", "aaram se bolo", "dheere dheere bolo",
        "धीरे", "धीरे बोलो", "धीरे से बोलो", "आराम से बोलो", "धीरे धीरे बोलो",
        "ਹੌਲੀ", "ਹੌਲੀ ਬੋਲੋ", "ਹੌਲੀ ਹੌਲੀ ਬੋਲੋ", "ਆਰਾਮ ਨਾਲ ਬੋਲੋ",
    ],
    "timer": [
        "timer", "how much time left", "how long left", "time left", "how much time", "how long",
        "timer kitna bacha", "kitna time bacha", "kitna time", "kitni der", "kitni der aur", "kitna bacha",
        "टाइमर", "टाइमर कितना बचा", "कितना टाइम बचा", "कितना टाइम", "कितनी देर", "कितनी देर और", "कितना बचा",
        "ਟਾਈਮਰ", "ਕਿੰਨਾ ਟਾਈਮ ਰਹਿੰਦਾ", "ਕਿੰਨਾ ਸਮਾਂ ਰਹਿੰਦਾ", "ਕਿੰਨਾ ਟਾਈਮ", "ਕਿੰਨੀ ਦੇਰ",
    ],
}

PUNCTUATION = re.compile(r"[^\w\sऀ-ॿ਀-੿]|[।॥]")


def clean(text):
    """Lower case, no punctuation, no nukta, no filler words at either end."""
    text = PUNCTUATION.sub(" ", text.lower()).replace("़", "").replace("਼", "")
    words = text.split()
    while words and words[0] in FILLER:
        words.pop(0)
    while words and words[-1] in FILLER:
        words.pop()
    return " ".join(words)


LOOKUP = {clean(phrase): intent for intent, phrases in COMMANDS.items() for phrase in phrases}

# What she says before reading the step (the screen shows only this part)
SAY = {
    "next": {"hi-en": "ठीक है बेटा।", "hi": "ठीक है बेटा।", "pa": "ਠੀਕ ਹੈ ਬੇਟਾ।", "en": "Okay, बेटा."},
    "previous": {"hi-en": "ठीक है, पिछला स्टेप।", "hi": "ठीक है, पिछला स्टेप।", "pa": "ਠੀਕ ਹੈ, ਪਿਛਲਾ ਸਟੈਪ।",
                 "en": "Okay, the step before."},
    "first": {"hi-en": "यह पहला ही स्टेप है बेटा।", "hi": "यह पहला ही स्टेप है बेटा।", "pa": "ਇਹ ਪਹਿਲਾ ਹੀ ਸਟੈਪ ਹੈ ਬੇਟਾ।",
              "en": "This is the first step, बेटा."},
    "repeat": {"hi-en": "सुनो बेटा।", "hi": "सुनो बेटा।", "pa": "ਸੁਣੋ ਬੇਟਾ।", "en": "Listen, बेटा."},
    "slow": {"hi-en": "ठीक है, धीरे बोलती हूँ।", "hi": "ठीक है, धीरे बोलती हूँ।", "pa": "ਠੀਕ ਹੈ, ਹੌਲੀ ਬੋਲਦੀ ਹਾਂ।",
             "en": "Okay, I'll say it slowly."},
    "finished": {"hi-en": "बस बेटा, हो गया!", "hi": "बस बेटा, हो गया!", "pa": "ਬੱਸ ਬੇਟਾ, ਹੋ ਗਿਆ!",
                 "en": "That's it, बेटा, all done!"},
}

TOOL = {"next": "next_step", "previous": "previous_step", "repeat": "repeat_step", "slow": "repeat_step",
        "timer": "check_timer"}


def match(text):
    return LOOKUP.get(clean(text))


def answer(state, intent):
    """Carry out the command and write her reply. Returns (tool, args, effect, said, spoken)."""
    recipe = RECIPES[state["recipe_id"]]
    lang = state["language"]
    voice = "hi" if lang == "hi-en" else lang  # Timbre reads Devanagari for Hinglish
    args = {"slow": True} if intent == "slow" else {}
    if intent == "timer":
        said = timer_reply(state)
        return TOOL[intent], args, {}, said, said
    was = state["current_step"]
    effect = apply_tool(state, TOOL[intent], args)
    if effect.get("finished"):
        said = SAY["finished"][lang]
        return TOOL[intent], args, effect, said, said
    key = "first" if intent == "previous" and was == 1 else intent
    said = SAY[key][lang]
    return TOOL[intent], args, effect, said, f"{said} {step_text(recipe, state['current_step'], voice)}"

"""Spot quantity words (do, aadha, chammach...) in a sentence, whether STT wrote it in Latin or Devanagari."""
import re

# The same quantity word in Latin (what en-IN writes) and Devanagari (what hi-IN writes).
QUANTITY_WORDS = {
    "1": ["ek", "1", "एक", "१"],
    "2": ["do", "2", "दो", "२"],
    "3": ["teen", "3", "तीन", "३"],
    "4": ["char", "chaar", "4", "चार", "४"],
    "5": ["paanch", "panch", "5", "पांच", "पाँच", "५"],
    "10": ["das", "dus", "10", "दस", "१०"],
    "15": ["pandrah", "pandra", "15", "पंद्रह", "१५"],
    "half": ["aadha", "adha", "aadhi", "half", "आधा", "आधी"],
    "1.5": ["dedh", "डेढ़", "डेढ"],
    "spoon": ["chammach", "chamach", "chammch", "spoon", "चम्मच"],
    "cup": ["cup", "कप"],
    "pinch": ["chutki", "pinch", "चुटकी"],
    "glass": ["glass", "gilas", "गिलास", "ग्लास"],
    "katori": ["katori", "bowl", "कटोरी"],
    "gram": ["gram", "grams", "ग्राम"],
    "minute": ["minute", "minutes", "minat", "मिनट"],
}
WORD_TO_QTY = {w: q for q, words in QUANTITY_WORDS.items() for w in words}


def quantities(text):
    """Which quantity ideas (2, half, spoon...) appear in a sentence, whatever the script."""
    tokens = re.findall(r"[^\s.,!?।|\"'()\-:;]+", text.lower())
    return {WORD_TO_QTY[t] for t in tokens if t in WORD_TO_QTY}

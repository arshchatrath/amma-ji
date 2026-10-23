# Amma ji design notes

What the app should feel like: a loud, happy Indian kitchen, not a chatbot. Readable from the stove.

## Palette (all in `src/styles/tokens.css`)

| Name | Hex | Used for |
|---|---|---|
| Haldi | `#f6b70e` | Start screen field, timer, anything active |
| Haldi soft | `#fce7a6` | Amma ji's speech bubble |
| Jamun | `#2a1533` | All main text, the kadhai rim, the big button |
| Jamun soft | `#5b4766` | Secondary text |
| Steel | `#e8ebed` | Cooking mode background (a steel thali) |
| Steel mid | `#6e7780` | Borders only, never text (fails AA for text) |
| Matka | `#b23a22` | Stop, safety notes |
| Dhaniya | `#2e6b45` | Timer done, safe |

Why not cream and terracotta: that pairing is the most common look of AI-made pages. The brief's
haldi, terracotta, steel and paper are kept, but haldi leads and terracotta is only for Stop.

## Type

Anek (Latin, Devanagari, Gurmukhi), one variable family with width and weight axes, so Hinglish,
Hindi and Punjabi share one voice. Wordmark: width 125%, weight 800. Steps: weight 650, very large.

## The one bold thing

The kadhai (`src/components/Kadhai.jsx`) is Amma ji's face and the mic button. Its seeds splutter
while she listens, get stirred while she thinks, and the oil ripples while she speaks. Everything
around it stays quiet. The only entrance animation is the tadka dropping in on the start screen.

## Rules

- No emojis, no em dashes in UI copy, sentence case
- Tap targets at least 56px (50px for the secondary row)
- Motion only for state changes, and none when the phone asks for reduced motion
- Room for a 3D kadhai later (img2three) in the same spot, if we make one

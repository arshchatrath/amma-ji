import "./Kadhai.css";

// A kadhai seen from above, with haldi oil and a tadka of mustard seeds and jeera.
// It is Amma ji's face in the app. Its `mood` shows what she is doing:
//   idle      seeds resting
//   listening seeds splutter, like mustard hitting hot oil
//   thinking  seeds get stirred round
//   speaking  the oil ripples outward
//   muted     the flame is off, everything goes grey
//   intro     seeds drop in one by one (the start screen's single entrance)

// Fixed seed positions, so the tadka looks the same on every visit.
function makeSeeds() {
  let s = 7;
  const rand = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const seeds = [];
  while (seeds.length < 22) {
    const angle = rand() * Math.PI * 2;
    const dist = 8 + rand() * 50;
    const x = 100 + Math.cos(angle) * dist;
    const y = 100 + Math.sin(angle) * dist;
    if (seeds.every((o) => Math.hypot(o.x - x, o.y - y) > 11)) {
      seeds.push({ x, y, jeera: seeds.length % 4 === 3, turn: Math.round(rand() * 180) });
    }
  }
  return seeds;
}
const SEEDS = makeSeeds();

export default function Kadhai({ mood = "idle", size = 200 }) {
  return (
    <svg
      className={`kadhai kadhai--${mood}`}
      viewBox="0 0 200 200"
      width={size}
      height={size}
      aria-hidden="true"
    >
      <defs>
        <radialGradient id="steel" cx="35%" cy="30%" r="80%">
          <stop offset="0" stopColor="var(--steel-shine)" />
          <stop offset="0.55" stopColor="var(--steel)" />
          <stop offset="1" stopColor="var(--steel-mid)" />
        </radialGradient>
      </defs>

      {/* handles */}
      <rect className="kadhai__handle" x="2" y="88" width="26" height="24" rx="12" />
      <rect className="kadhai__handle" x="172" y="88" width="26" height="24" rx="12" />

      {/* rim and oil */}
      <circle className="kadhai__rim" cx="100" cy="100" r="84" fill="url(#steel)" />
      <circle className="kadhai__oil" cx="100" cy="100" r="68" />
      <circle className="kadhai__ripple" cx="100" cy="100" r="40" />
      <circle className="kadhai__ripple kadhai__ripple--late" cx="100" cy="100" r="40" />

      <g className="kadhai__seeds">
        {/* each seed sits in its own group, so the animation does not undo the jeera's tilt */}
        {SEEDS.map((seed, i) => (
          <g key={i} className={`kadhai__seed${seed.jeera ? " kadhai__seed--jeera" : ""}`} style={{ "--i": i }}>
            {seed.jeera ? (
              <ellipse
                cx={seed.x}
                cy={seed.y}
                rx="5.5"
                ry="2"
                transform={`rotate(${seed.turn} ${seed.x} ${seed.y})`}
              />
            ) : (
              <circle cx={seed.x} cy={seed.y} r="3.6" />
            )}
          </g>
        ))}
      </g>
    </svg>
  );
}

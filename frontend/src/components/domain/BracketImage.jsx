// Lays the seeded field onto the provided CFP bracket artwork by overlaying
// each team's logo next to its seed number. `seeds` is a map of seed (1-12) to
// { team, abbr, espn_id }. Positions are percentages of the image so the
// overlay scales with the artwork.
const SRC = '/cfb_bracket.png';

// Center of each logo, as a percentage of the bracket image (1200x630).
// Derived by detecting each gold box: the seed number sits on the LEFT of every
// box, so the logo goes in the empty team area to its right.
const SEED_POS = {
  8: { x: 10.0, y: 14.3 },
  9: { x: 10.0, y: 26.3 },
  1: { x: 27.5, y: 31.0 },
  4: { x: 28.0, y: 60.0 },
  5: { x: 10.0, y: 74.0 },
  12: { x: 10.0, y: 86.0 },
  7: { x: 92.0, y: 14.5 },
  10: { x: 92.0, y: 26.5 },
  2: { x: 74.3, y: 31.5 },
  3: { x: 74.3, y: 60.0 },
  6: { x: 92.0, y: 73.0 },
  11: { x: 92.0, y: 85.0 },
};

function logoUrl(espnId) {
  return espnId ? `https://a.espncdn.com/i/teamlogos/ncaa/500/${espnId}.png` : null;
}

export default function BracketImage({ seeds = {} }) {
  return (
    <div className="bracket-image">
      <img className="bracket-bg" src={SRC} alt="College Football Playoff bracket" />
      {Object.entries(SEED_POS).map(([seed, pos]) => {
        const t = seeds[seed];
        if (!t) return null;
        const url = logoUrl(t.espn_id);
        return (
          <span className="bracket-slot" key={seed} style={{ left: `${pos.x}%`, top: `${pos.y}%` }} title={`#${seed} ${t.team}`}>
            {url ? <img src={url} alt={t.abbr || t.team} /> : <span className="bs-abbr">{t.abbr}</span>}
          </span>
        );
      })}
    </div>
  );
}

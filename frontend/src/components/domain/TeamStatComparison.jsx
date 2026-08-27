// Side-by-side team stat comparison (home vs away), each row a labeled pair with
// a split bar weighted by the two values. Reads a game's `team_stats` block.
const ROWS = [
  { key: 'total_yards', label: 'Total Yards' },
  { key: 'pass_yards', label: 'Passing Yards' },
  { key: 'rush_yards', label: 'Rushing Yards' },
  { key: 'first_downs', label: 'First Downs' },
  { key: 'third_down', label: 'Third Down', text: true },
  { key: 'red_zone', label: 'Red Zone', text: true },
  { key: 'turnovers', label: 'Turnovers', lowGood: true },
  { key: 'sacks', label: 'Sacks' },
  { key: 'penalties', label: 'Penalties', text: true },
  { key: 'time_of_possession', label: 'Time of Possession', text: true, toSecs: true },
];

function num(v, toSecs) {
  if (toSecs && typeof v === 'string' && v.includes(':')) {
    const [m, s] = v.split(':'); return Number(m) * 60 + Number(s);
  }
  if (typeof v === 'string') { const m = v.match(/-?\d+/); return m ? Number(m[0]) : 0; }
  return Number(v) || 0;
}

export default function TeamStatComparison({ game }) {
  const ts = game?.team_stats;
  if (!ts) return null;
  const { home, away } = ts;
  return (
    <div className="gc-compare">
      <div className="gc-compare-head">
        <span>{game.away?.abbr}</span>
        <span className="gc-compare-title">Team Stats</span>
        <span>{game.home?.abbr}</span>
      </div>
      {ROWS.map((r) => {
        const a = away[r.key];
        const h = home[r.key];
        const an = num(a, r.toSecs);
        const hn = num(h, r.toSecs);
        const total = an + hn || 1;
        const awayPct = Math.round((an / total) * 100);
        return (
          <div className="gc-stat-row" key={r.key}>
            <span className="gc-stat-val">{a}</span>
            <div className="gc-stat-mid">
              <span className="gc-stat-label">{r.label}</span>
              <div className="gc-bar">
                <span className="gc-bar-away" style={{ width: `${awayPct}%` }} />
                <span className="gc-bar-home" style={{ width: `${100 - awayPct}%` }} />
              </div>
            </div>
            <span className="gc-stat-val">{h}</span>
          </div>
        );
      })}
    </div>
  );
}

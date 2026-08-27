import { noEmDash } from '../../lib/format.js';

// The scoring plays in order, grouped by quarter, each showing the team, the
// play type, the description, and the running score. Reads a game's
// `scoring_summary` list.
const TYPE_LABEL = { TD: 'TD', FG: 'FG', Safety: 'SAF' };

export default function ScoringSummary({ scoring = [] }) {
  if (!scoring.length) return <div className="gc-empty">No scoring plays.</div>;
  const byQuarter = [];
  let cur = null;
  for (const s of scoring) {
    if (!cur || cur.q !== s.quarter) { cur = { q: s.quarter, items: [] }; byQuarter.push(cur); }
    cur.items.push(s);
  }
  const qLabel = (q) => (q === 'OT' ? 'Overtime' : `${q}Q`);
  return (
    <div className="gc-scoring">
      {byQuarter.map((grp) => (
        <div className="gc-scoring-q" key={grp.q}>
          <div className="gc-scoring-qhead">{qLabel(grp.q)}</div>
          {grp.items.map((s, i) => (
            <div className="gc-scoring-row" key={i}>
              <span className={`gc-scoring-type type-${s.type.toLowerCase()}`}>{TYPE_LABEL[s.type] || s.type}</span>
              <span className="gc-scoring-team">{s.team_abbr}</span>
              <span className="gc-scoring-detail">{noEmDash(s.detail)}</span>
              <span className="gc-scoring-score">{s.away_score}-{s.home_score}</span>
              <span className="gc-scoring-clock">{s.clock}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

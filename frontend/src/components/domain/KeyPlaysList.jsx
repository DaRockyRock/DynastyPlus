import { noEmDash } from '../../lib/format.js';

// The turning points: scores, turnovers, and explosive plays, each tagged by
// kind. Reads a game's `key_plays` list.
const KIND_CLASS = {
  TD: 'good', FG: 'good', Turnover: 'bad', Explosive: 'big', Safety: 'bad',
};

export default function KeyPlaysList({ plays = [] }) {
  if (!plays.length) return <div className="gc-empty">No key plays.</div>;
  return (
    <div className="gc-keyplays">
      {plays.map((p, i) => (
        <div className="gc-keyplay" key={i}>
          <span className={`gc-keyplay-kind ${KIND_CLASS[p.kind] || ''}`}>{p.kind}</span>
          <span className="gc-keyplay-time">{p.quarter === 'OT' ? 'OT' : `${p.quarter}Q`} {p.clock}</span>
          <span className="gc-keyplay-team">{p.team_abbr}</span>
          <span className="gc-keyplay-desc">{noEmDash(p.description)}</span>
        </div>
      ))}
    </div>
  );
}

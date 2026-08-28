import TeamLogo from '../ui/TeamLogo.jsx';

// How the field was picked: auto-bids, teams disqualified by the format's
// rules, first teams out, and any selection notes from the engine
// (backend/playoff.select_field). Renders nothing when there is nothing to say.
function TeamLine({ entry, tag, reason }) {
  return (
    <li>
      <TeamLogo espnId={entry.espn_id} abbr={entry.abbr} name={entry.team} size={20} />
      <span>{entry.team}</span>
      {tag && <span className="pfe-badge">{tag}</span>}
      {reason && <span className="pfe-reason">{reason}</span>}
    </li>
  );
}

export default function PlayoffSelectionSummary({ selection }) {
  if (!selection) return null;
  const { auto_bids: autoBids = [], excluded = [], first_out: firstOut = [], notes = [] } = selection;
  if (!autoBids.length && !excluded.length && !firstOut.length && !notes.length) return null;

  return (
    <div className="pfe-stack">
      {notes.map((n, i) => <p className="pb-note" key={i}>{n}</p>)}
      {autoBids.length > 0 && (
        <div>
          <div className="cfp-bracket-label">Automatic bids</div>
          <ul className="pfe-selection-list">
            {autoBids.map((t) => <TeamLine key={t.team} entry={t} tag={`Seed ${t.seed}`} />)}
          </ul>
        </div>
      )}
      {excluded.length > 0 && (
        <div>
          <div className="cfp-bracket-label">Disqualified by format rules</div>
          <ul className="pfe-selection-list">
            {excluded.map((t) => <TeamLine key={t.team} entry={t} reason={t.reason} />)}
          </ul>
        </div>
      )}
      {firstOut.length > 0 && (
        <div>
          <div className="cfp-bracket-label">First teams out</div>
          <ul className="pfe-selection-list">
            {firstOut.map((t) => <TeamLine key={t.team} entry={t} />)}
          </ul>
        </div>
      )}
    </div>
  );
}

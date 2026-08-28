import { useState, useEffect } from 'react';
import Modal from '../ui/Modal.jsx';
import TeamLogo from '../ui/TeamLogo.jsx';
import ConferenceLogo from '../ui/ConferenceLogo.jsx';

// Destination picker for moving one team: lists every other conference
// (including the Independents pool) with its logo, member count, and a
// full / under-minimum state. Full destinations are disabled. Divisioned
// destinations expand to ask which division the team lands in. Calls
// `onMove({ toId, division })`; the page applies the draft mutation.
export default function TeamMovePicker({
  open, team, teamsByName = {}, conferences = [], fromId, onMove, onClose,
}) {
  const [expanded, setExpanded] = useState(null);
  useEffect(() => { setExpanded(null); }, [open, team]);

  const entry = team ? teamsByName[team] : null;
  const targets = conferences.filter((c) => c && c.id !== fromId);

  const pick = (conf) => {
    if ((conf.divisions || []).length >= 2) {
      setExpanded(expanded === conf.id ? null : conf.id);
      return;
    }
    onMove?.({ toId: conf.id, division: null });
  };

  return (
    <Modal open={open} onClose={onClose} align="center">
      {open && (
        <div className="cs-picker modal-card">
          <div className="cs-picker-head">
            <TeamLogo espnId={entry?.espn_id} name={team} abbr={entry?.abbreviation} logo={entry?.logo || ''} size={40} />
            <span className="cs-picker-titles">
              <div className="cs-picker-title">Move {entry?.school || team}</div>
              <div className="cs-picker-sub">Pick the destination conference.</div>
            </span>
            <button className="bm-close" onClick={onClose} aria-label="Close">&times;</button>
          </div>
          <div className="cs-picker-body">
            {targets.map((conf) => {
              const n = (conf.teams || []).length;
              const full = !!conf.limits && n >= conf.limits.max;
              const under = !!conf.limits && n < conf.limits.min;
              const divisioned = (conf.divisions || []).length >= 2;
              return (
                <div key={conf.id}>
                  <button
                    className="cs-dest"
                    disabled={full}
                    onClick={() => pick(conf)}
                    title={full ? `${conf.name} is at its ${conf.limits.max}-team capacity` : undefined}
                  >
                    <ConferenceLogo name={conf.name} size={26} title={conf.name} />
                    <span className="cs-dest-id">
                      <span className="cs-dest-name">{conf.name}</span>
                      <span className="cs-dest-meta">
                        {n} team{n === 1 ? '' : 's'}
                        {conf.independents ? ', independents pool' : ''}
                        {!conf.in_game ? ', companion only' : ''}
                        {divisioned ? `, ${conf.divisions.length} divisions` : ''}
                      </span>
                    </span>
                    {full && <span className="cs-dest-state full">Full</span>}
                    {!full && under && <span className="cs-dest-state under">Under min</span>}
                  </button>
                  {divisioned && expanded === conf.id && (
                    <div className="cs-dest-divs">
                      {conf.divisions.map((d) => (
                        <button
                          key={d.name}
                          className="cs-dest-div"
                          onClick={() => onMove?.({ toId: conf.id, division: d.name })}
                        >
                          {conf.name} {d.name}
                          <span>{(d.teams || []).length} teams</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </Modal>
  );
}

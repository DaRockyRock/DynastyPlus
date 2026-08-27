import TeamLogo from '../ui/TeamLogo.jsx';

// FBS team picker: a native select grouped by conference, with a live logo
// preview of the chosen program. Used on the Simulator's season-start screen to
// change the user's team before kickoff. `teams` is the FBS list from
// /api/sim/fbs-teams ({ name, conference, espn_id, abbreviation, color, logo }).
export default function TeamSelect({ teams = [], value, onChange, disabled = false, placeholder = 'Select a team' }) {
  // Group by conference, preserving the order conferences first appear (the
  // league seed already clusters teams by conference).
  const order = [];
  const byConf = {};
  for (const t of teams) {
    const c = t.conference || 'Other';
    if (!byConf[c]) { byConf[c] = []; order.push(c); }
    byConf[c].push(t);
  }
  const match = teams.find((t) => t.name === value) || null;

  return (
    <div className="team-select">
      <span className="ts-logo">
        <TeamLogo espnId={match?.espn_id} name={value} abbr={match?.abbreviation} color={match?.color} size={40} />
      </span>
      <select
        className="set-select ts-select"
        value={value || ''}
        disabled={disabled}
        onChange={(e) => onChange?.(e.target.value)}
      >
        {!value && <option value="" disabled>{placeholder}</option>}
        {order.map((conf) => (
          <optgroup key={conf} label={conf}>
            {byConf[conf].map((t) => (
              <option key={t.name} value={t.name}>{t.name}</option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  );
}

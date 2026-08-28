import TeamLogo from '../ui/TeamLogo.jsx';

// Conference-grouped team control used on either side of a bowl matchup.
// Selecting a team from another bowl triggers an atomic swap in the editor.
export default function BowlTeamPicker({
  label,
  teams = [],
  value,
  onChange,
  disabled = false,
}) {
  const selected = teams.find((team) => team.row === Number(value));
  const byConference = new Map();
  for (const team of teams) {
    const conference = team.conference || 'Other';
    if (!byConference.has(conference)) byConference.set(conference, []);
    byConference.get(conference).push(team);
  }
  return (
    <label className="bowl-team-picker">
      <span className="btp-label">{label}</span>
      <span className="btp-control">
        <TeamLogo
          espnId={selected?.espn_id}
          abbr={selected?.abbr}
          name={selected?.name}
          color={selected?.color}
          size={32}
        />
        <select
          className="set-select"
          value={value ?? ''}
          disabled={disabled}
          onChange={(event) => onChange?.(Number(event.target.value))}
        >
          {[...byConference.entries()].map(([conference, rows]) => (
            <optgroup key={conference} label={conference}>
              {rows.map((team) => (
                <option key={team.row} value={team.row}>
                  {team.rank ? `#${team.rank} ` : ''}{team.name} ({team.record})
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </span>
    </label>
  );
}

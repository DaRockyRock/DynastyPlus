import TeamHelmet from '../ui/TeamHelmet.jsx';

// The game's matchup splash: two rendered helmets facing each other around an
// AT/VS puck, with optional hero-style names and records underneath.
// `away`/`home` = { espn_id, name, abbr, record, color }.
export default function HelmetMatchup({ away, home, size = 110, mark = 'AT', showNames = true }) {
  // Both sides render the same rows (helmet shell, name, record) with
  // reserved space, and the shell bottom-aligns the art, so the two helmets
  // always sit level regardless of per-team art padding or a missing record.
  const side = (team, facing) => (
    <span className="hm-side" key={facing}>
      <span className="hm-shell">
        <TeamHelmet
          espnId={team?.espn_id}
          abbr={team?.abbr}
          name={team?.name}
          color={team?.color}
          side={facing}
          size={size}
        />
      </span>
      {showNames && <span className="hm-name">{team?.name || ' '}</span>}
      {showNames && <span className="hm-rec">{team?.record || ' '}</span>}
    </span>
  );
  return (
    <div className="helmet-matchup" style={{ '--hm-size': `${size}px` }}>
      {side(away, 'right')}
      <span className="hm-at">{mark}</span>
      {side(home, 'left')}
    </div>
  );
}

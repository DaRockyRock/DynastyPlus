import TeamLogo from '../ui/TeamLogo.jsx';

// A single ranking row: number, real logo, team, abbreviation, record.
export function RankRow({ row, isUser = false }) {
  return (
    <div className={`rank-row${isUser ? ' is-user' : ''}`}>
      <span className="rank-num">{row.rank}</span>
      <TeamLogo espnId={row.espn_id} abbr={row.abbr} name={row.team} size={26} />
      <span className="rank-team">
        {row.team}
        {row.first ? <span className="rank-first"> ({row.first})</span> : null}
      </span>
      <span className="rank-abbr">{row.abbr}</span>
      <span className="rank-rec">{row.record}</span>
      {row.points != null && <span className="rank-points">{row.points.toLocaleString()}</span>}
    </div>
  );
}

// Ranked list of teams (CFP / AP / standings). Highlights the user's team.
export default function RankingList({ teams = [], userTeam, max }) {
  const rows = max ? teams.slice(0, max) : teams;
  return (
    <div>
      {rows.map((r) => (
        <RankRow key={`${r.rank}-${r.team}`} row={r} isUser={r.team === userTeam} />
      ))}
    </div>
  );
}

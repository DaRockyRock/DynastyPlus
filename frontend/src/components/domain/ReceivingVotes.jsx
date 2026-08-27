import TeamLogo from '../ui/TeamLogo.jsx';

// "Receiving Votes" section for the AP and Coaches polls: teams just outside
// the top 25 with their vote totals.
export default function ReceivingVotes({ teams = [] }) {
  if (!teams.length) return null;
  return (
    <div className="receiving-votes">
      <div className="rv-title">Receiving Votes</div>
      <div className="rv-list">
        {teams.map((t, i) => (
          <span className="rv-item" key={i}>
            <TeamLogo espnId={t.espn_id} abbr={t.abbr} name={t.team} size={18} />
            <span className="rv-team">{t.team}</span>
            <b className="rv-votes">{t.votes}</b>
          </span>
        ))}
      </div>
    </div>
  );
}

import Card from '../ui/Card.jsx';
import TeamLogo from '../ui/TeamLogo.jsx';

// Upcoming-opponent card. Layout:
//   header bar (NEXT UP label + WEEK badge)
//   opponent row (logo | rank + name + record + home/away)
//   info strip (kickoff | TV | spread) with divider above
export default function NextGameCard({ game }) {
  const up = game;
  return (
    <Card className="next-card">
      <div className="next-header">
        <span className="next-label">Next Up</span>
        <span className="next-week-badge">Wk {up.week}</span>
      </div>
      <div className="next-body">
        <TeamLogo espnId={up.opponent_espn_id} abbr={up.opponent_abbr} name={up.opponent} size={52} />
        <div className="next-opp">
          {up.opponent_rank && <span className="next-rank">#{up.opponent_rank}</span>}
          <span className="next-opp-name">{up.opponent}</span>
          <span className="next-opp-meta">
            {up.opponent_record}
            <span className="next-sep" />
            <span className={`next-site ${up.home ? 'is-home' : 'is-away'}`}>{up.home ? 'Home' : 'Away'}</span>
          </span>
        </div>
      </div>
      <div className="next-info">
        {up.kickoff && <span className="ni-item"><span className="ni-val">{up.kickoff}</span></span>}
        {up.tv && <span className="ni-item"><span className="ni-label">TV</span><span className="ni-val">{up.tv}</span></span>}
        {up.spread && <span className="ni-item"><span className="ni-label">Line</span><span className="ni-val">{up.spread}</span></span>}
      </div>
    </Card>
  );
}

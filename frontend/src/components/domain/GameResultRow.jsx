import Card from '../ui/Card.jsx';
import TeamLogo from '../ui/TeamLogo.jsx';

// One game in the weekly scoreboard, read as a broadcast score-bug: the
// away team stacked over the home team, each with its logo, AP rank, name, and
// (when final) score. The winner is emphasized and the user's own game is
// accented. `game` is a /api/sim/scoreboard row.
function TeamLine({ team, score, winner, final }) {
  const cls = ['sb-team', winner ? 'is-win' : '', team.is_user ? 'is-user' : ''].filter(Boolean).join(' ');
  return (
    <div className={cls}>
      <TeamLogo espnId={team.espn_id} abbr={team.abbr} name={team.name} size={24} />
      {team.rank && <span className="sb-rank">{team.rank}</span>}
      <span className="sb-name">{team.name}</span>
      <span className="sb-score">{final ? score : ''}</span>
    </div>
  );
}

export default function GameResultRow({ game }) {
  const final = game.status === 'final';
  return (
    <Card className={['sb-row', game.user ? 'is-user' : ''].filter(Boolean).join(' ')}>
      <div className="sb-meta">
        <span className="sb-status">{final ? 'Final' : 'Saturday'}</span>
        {game.user && <span className="sb-yours">Your Game</span>}
        {game.override && <span className="sb-override">Edited</span>}
        {game.label && <span className="sb-label">{game.label}</span>}
        {game.neutral && !game.label && <span className="sb-neutral">Neutral</span>}
      </div>
      <div className="sb-teams">
        <TeamLine team={game.away} score={game.away_score} final={final}
                  winner={final && game.winner === game.away.name} />
        <TeamLine team={game.home} score={game.home_score} final={final}
                  winner={final && game.winner === game.home.name} />
      </div>
    </Card>
  );
}

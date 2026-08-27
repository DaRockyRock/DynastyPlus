import TeamLogo from '../ui/TeamLogo.jsx';
import Badge from '../ui/Badge.jsx';
import { noEmDash } from '../../lib/format.js';

// Broadcast final-score banner for a completed game: both teams with logos and
// scores, the winner highlighted, plus a week / final (or OT) tag. Reads a
// dynasty `last_game` object (or any game with home/away/final). `coaches` is the
// dynasty coaching directory (team name -> coach entity or name), so each team
// can show its head coach under the abbreviation.
export default function GameScoreHeader({ game, coaches = {} }) {
  if (!game) return null;
  const { home, away, final = {} } = game;
  const winner = final.winner;
  const coachOf = (team) => {
    const c = coaches?.[team.name];
    return (c && (c.name || c)) || '';
  };
  const Side = ({ team }) => {
    const win = winner === team.name;
    const coach = coachOf(team);
    return (
      <div className={`gc-team${win ? ' is-winner' : ''}`}>
        <TeamLogo espnId={team.espn_id} abbr={team.abbr} name={team.name} size={54} />
        <span className="gc-team-id">
          <span className="gc-team-abbr">{team.abbr}</span>
          {coach && <span className="gc-team-coach">{noEmDash(coach)}</span>}
        </span>
        <span className="gc-score-num">{team.score}</span>
      </div>
    );
  };
  return (
    <div className="gc-score">
      <Side team={away} />
      <div className="gc-score-mid">
        <Badge>{final.overtime ? 'FINAL / OT' : 'FINAL'}</Badge>
        <span className="gc-score-week">Week {game.week}{game.neutral ? ', neutral site' : ''}</span>
      </div>
      <Side team={home} />
    </div>
  );
}

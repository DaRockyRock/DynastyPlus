import TeamLogo from '../ui/TeamLogo.jsx';

// One game on a team's resume: result pill, score, venue, and the opponent
// with its current rank and record. `game` is one /api/rankings/resume game
// (or best_wins / worst_losses entry); `compact` drops the tags for the
// signature-win lists. Upcoming games (no `result`) render as matchup rows.
export default function ResumeGameRow({ game, compact = false }) {
  const opp = game.opponent || {};
  const won = game.result === 'W';
  const played = !!game.result;
  const venue = game.neutral ? 'N' : (game.home ? 'vs' : 'at');
  return (
    <div className={['resume-game', played ? (won ? 'is-win' : 'is-loss') : 'is-upcoming'].filter(Boolean).join(' ')}>
      {played && <span className="rg-result">{game.result}</span>}
      {played && <span className="rg-score">{game.score}</span>}
      <span className="rg-venue">{venue}</span>
      <TeamLogo espnId={opp.espn_id} logo={opp.logo} abbr={opp.abbr} name={opp.school} size={22} />
      <span className="rg-opp">
        {opp.cfp_rank && <span className="rg-opprank">#{opp.cfp_rank}</span>}
        {opp.school}
        <span className="rg-opprec">({opp.record || '0-0'})</span>
      </span>
      {!compact && game.label && <span className="rg-label">{game.label}</span>}
      {!compact && game.conference_game && !game.label && <span className="rg-conf">Conf</span>}
    </div>
  );
}

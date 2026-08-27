import Card from '../ui/Card.jsx';
import TeamLogo from '../ui/TeamLogo.jsx';
import { noEmDash } from '../../lib/format.js';

// Last-result broadcast chip. Reads left-to-right like a score-bug:
//   [opponent logo] [score] [W/L] [location + opponent + rank]
export default function ResultCard({ result, title = 'Last Result', onClick }) {
  const r = result;
  const win = r.result === 'W';
  return (
    <Card
      className={`result-card ${win ? 'result-win' : 'result-loss'}${onClick ? ' is-clickable' : ''}`}
      onClick={onClick}
    >
      <div className="result-header">
        <span className="result-label">{title}</span>
        <span className={`result-outcome ${win ? 'is-win' : 'is-loss'}`}>{win ? 'WIN' : 'LOSS'}</span>
      </div>
      <div className="result-body">
        <div className="result-logo-col">
          <TeamLogo espnId={r.opponent_espn_id} abbr={r.opponent_abbr} name={r.opponent} size={52} />
        </div>
        <div className="result-divider" />
        <div className="result-center">
          <div className="result-score">{r.score}</div>
          <div className="result-loc">{r.home ? 'vs' : 'at'} <span>{noEmDash(r.opponent)}</span></div>
          {r.rank_matchup && <div className="result-rank">{noEmDash(r.rank_matchup)}</div>}
        </div>
      </div>
    </Card>
  );
}

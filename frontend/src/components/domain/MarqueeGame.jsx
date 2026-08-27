import Card from '../ui/Card.jsx';
import TeamLogo from '../ui/TeamLogo.jsx';

// One game on the marquee matchups board (a decorated entry from
// lib/matchups: scoreboard game + {quality, tag}). `featured` renders the
// game-of-the-week treatment; the default is a compact slate row with the
// away team over the home team, scoreboard style.

function finalLine(game) {
  const homeWon = game.home_score > game.away_score;
  const w = homeWon ? game.home : game.away;
  const l = homeWon ? game.away : game.home;
  const ws = homeWon ? game.home_score : game.away_score;
  const ls = homeWon ? game.away_score : game.home_score;
  return `Final: ${w.abbr} ${ws}, ${l.abbr} ${ls}`;
}

function FeatureSide({ side }) {
  return (
    <div className="mq-side">
      <TeamLogo espnId={side.espn_id} abbr={side.abbr} name={side.name} size={56} />
      <div className="mq-side-rank">{side.rank ? `#${side.rank}` : 'NR'}</div>
      <div className="mq-side-name">{side.name}</div>
      <div className="mq-side-rec">{side.record}</div>
    </div>
  );
}

function RowTeam({ side, home }) {
  return (
    <div className="mq-row-team">
      {home ? <span className="mq-row-at">@</span> : <span className="mq-row-at is-blank" />}
      <TeamLogo espnId={side.espn_id} abbr={side.abbr} name={side.name} size={22} />
      <span className="mq-row-rank">{side.rank ? `#${side.rank}` : ''}</span>
      <span className="mq-row-name">{side.name}</span>
      <span className="mq-row-rec">{side.record}</span>
    </div>
  );
}

export default function MarqueeGame({ game, featured = false }) {
  const isFinal = game.status === 'final' && game.home_score != null;

  if (featured) {
    return (
      <Card className={`mq-feature${game.user ? ' is-user' : ''}`}>
        <div className="mq-head">
          <span className="mq-tag">{game.tag}</span>
          <span className="mq-quality" title="Matchup quality, from the rankings">
            <b>{game.quality}</b> Game Score
          </span>
        </div>
        <div className="mq-body">
          <FeatureSide side={game.away} />
          <div className="mq-at">{game.neutral ? 'VS' : 'AT'}</div>
          <FeatureSide side={game.home} />
        </div>
        <div className="mq-foot">
          {isFinal
            ? <span className="mq-final">{finalLine(game)}</span>
            : <>
                {game.line && <span className="mq-line">{game.line}</span>}
                <span className="mq-note">{game.conference_game ? 'Conference game' : 'Non-conference'}</span>
              </>}
        </div>
      </Card>
    );
  }

  return (
    <div className={`mq-row${game.user ? ' is-user' : ''}`}>
      <div className="mq-row-teams">
        <RowTeam side={game.away} />
        <RowTeam side={game.home} home />
      </div>
      <div className="mq-row-side">
        <span className="mq-row-line">{isFinal ? `${game.away_score}-${game.home_score} F` : game.line}</span>
        <span className="mq-row-q" title="Matchup quality, from the rankings">{game.quality}</span>
      </div>
    </div>
  );
}

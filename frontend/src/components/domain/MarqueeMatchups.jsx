import MarqueeGame from './MarqueeGame.jsx';
import { rankMatchups } from '../../lib/matchups.js';

// The week's biggest games. Takes the save's national scoreboard, ranks it
// with the rankings-driven matchup algorithm (lib/matchups), and renders the
// featured game of the week beside the rest of the board. Renders nothing
// when the save carries no national slate (older saves).
export default function MarqueeMatchups({ scoreboard = [], limit = 4 }) {
  const games = rankMatchups(scoreboard, { limit });
  if (!games.length) return null;
  const [feature, ...rest] = games;

  return (
    <div className="marquee">
      <MarqueeGame game={feature} featured />
      {rest.length > 0 && (
        <div className="marquee-board">
          {rest.map((g) => (
            <MarqueeGame key={`${g.away?.name}-${g.home?.name}`} game={g} />
          ))}
        </div>
      )}
    </div>
  );
}

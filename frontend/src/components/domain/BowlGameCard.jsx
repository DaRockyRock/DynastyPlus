import BowlLogo from './BowlLogo.jsx';
import BowlTeamPicker from './BowlTeamPicker.jsx';
import HelmetMatchup from './HelmetMatchup.jsx';

// Broadcast-quality bowl matchup card. The bowl owns the visual hierarchy,
// followed by the two facing game helmets, then the precise assignment tools.
export default function BowlGameCard({
  game,
  teams = [],
  assignment,
  onChange,
  editable = true,
  dirty = false,
}) {
  if (!game || !assignment) return null;
  const away = teams.find((team) => team.row === assignment.away_row) || game.away;
  const home = teams.find((team) => team.row === assignment.home_row) || game.home;
  const locked = !editable || game.official;
  return (
    <article className={`bowl-game-card${game.ny6 ? ' ny6' : ''}${dirty ? ' dirty' : ''}${locked ? ' locked' : ''}`}>
      <header className="bgc-head">
        <span className="bgc-tier">{game.ny6 ? "New Year's Six" : 'Bowl Season'}</span>
        <span className={`bgc-state${dirty ? ' changed' : ''}`}>
          {game.official ? 'Final' : dirty ? 'Changed' : 'Assigned'}
        </span>
      </header>
      <div className="bgc-brand">
        <BowlLogo asset={game.asset} name={game.name} size={game.ny6 ? 118 : 96} />
        <div className="bgc-title">
          <h3>{game.name}</h3>
          <p>{[game.venue, game.city].filter(Boolean).join(' | ')}</p>
        </div>
      </div>
      <div className="bgc-matchup">
        <HelmetMatchup away={away} home={home} size={game.ny6 ? 102 : 88} mark="VS" />
      </div>
      <div className="bgc-pickers">
        <BowlTeamPicker
          label="Away team"
          teams={teams}
          value={assignment.away_row}
          disabled={locked}
          onChange={(row) => onChange?.('away_row', row)}
        />
        <BowlTeamPicker
          label="Home team"
          teams={teams}
          value={assignment.home_row}
          disabled={locked}
          onChange={(row) => onChange?.('home_row', row)}
        />
      </div>
    </article>
  );
}

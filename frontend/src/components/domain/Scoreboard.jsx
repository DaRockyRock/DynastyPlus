import SectionTitle from '../ui/SectionTitle.jsx';
import EmptyState from '../ui/EmptyState.jsx';
import GameResultRow from './GameResultRow.jsx';

// The week's full slate of simulated games as a grid of score-bug rows. Title
// shows the week and game count; an optional `right` node (e.g. a week stepper)
// rides the title row.
export default function Scoreboard({ week, games = [], title, right }) {
  return (
    <div className="scoreboard">
      <SectionTitle right={right}>
        {title || `Week ${week} Scoreboard`}
        <span className="sb-count">{games.length}</span>
      </SectionTitle>
      {games.length === 0 ? (
        <EmptyState>No games scheduled for this week.</EmptyState>
      ) : (
        <div className="sb-grid">
          {games.map((g, i) => <GameResultRow key={`${g.home.name}-${g.away.name}-${i}`} game={g} />)}
        </div>
      )}
    </div>
  );
}

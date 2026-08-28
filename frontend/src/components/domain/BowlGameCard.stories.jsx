import BowlGameCard from './BowlGameCard.jsx';
import { bowlGameTeams, bowlGamesState } from '../fixtures.js';

export default { title: 'Domain/BowlGameCard', component: BowlGameCard };

const game = bowlGamesState.games[0];
const assignment = bowlGamesState.assignments[0];

export const Marquee = {
  render: () => (
    <div style={{ width: 520, padding: 24 }}>
      <BowlGameCard game={game} teams={bowlGameTeams} assignment={assignment} onChange={() => {}} />
    </div>
  ),
};

export const Changed = {
  render: () => (
    <div style={{ width: 520, padding: 24 }}>
      <BowlGameCard game={bowlGamesState.games[1]} teams={bowlGameTeams} assignment={bowlGamesState.assignments[1]} dirty onChange={() => {}} />
    </div>
  ),
};

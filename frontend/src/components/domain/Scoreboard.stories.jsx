import Scoreboard from './Scoreboard.jsx';
import { scoreboardGames } from '../fixtures.js';

export default {
  title: 'Domain/Scoreboard',
  component: Scoreboard,
  parameters: { layout: 'padded' },
};

export const Default = { render: () => <div style={{ width: 760 }}><Scoreboard week={5} games={scoreboardGames} /></div> };

export const Empty = { render: () => <div style={{ width: 760 }}><Scoreboard week={1} games={[]} /></div> };

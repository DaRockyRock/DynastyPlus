import GameResultRow from './GameResultRow.jsx';
import { scoreboardGames, scoreboardUpcoming } from '../fixtures.js';

export default {
  title: 'Domain/GameResultRow',
  component: GameResultRow,
  parameters: { layout: 'padded' },
};

export const UserWin = { render: () => <div style={{ width: 340 }}><GameResultRow game={scoreboardGames[0]} /></div> };

export const RankedMatchup = { render: () => <div style={{ width: 340 }}><GameResultRow game={scoreboardGames[1]} /></div> };

export const Upset = { render: () => <div style={{ width: 340 }}><GameResultRow game={scoreboardGames[2]} /></div> };

export const Scheduled = { render: () => <div style={{ width: 340 }}><GameResultRow game={scoreboardUpcoming[0]} /></div> };

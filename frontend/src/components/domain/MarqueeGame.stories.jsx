import MarqueeGame from './MarqueeGame.jsx';
import { nationalScoreboard } from '../fixtures.js';
import { rankMatchups } from '../../lib/matchups.js';

const board = rankMatchups(nationalScoreboard, { limit: 5 });

export default {
  title: 'Domain/MarqueeGame',
  component: MarqueeGame,
  parameters: { layout: 'centered' },
};

export const Featured = {
  render: () => <div style={{ width: 480 }}><MarqueeGame game={board[0]} featured /></div>,
};
export const FeaturedUserGame = {
  render: () => <div style={{ width: 480 }}><MarqueeGame game={board.find((g) => g.user)} featured /></div>,
};
export const Row = {
  render: () => <div style={{ width: 380 }}><MarqueeGame game={board[1]} /></div>,
};
export const RowFinal = {
  render: () => <div style={{ width: 380 }}><MarqueeGame game={board.find((g) => g.status === 'final')} /></div>,
};

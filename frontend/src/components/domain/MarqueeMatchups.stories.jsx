import MarqueeMatchups from './MarqueeMatchups.jsx';
import { nationalScoreboard } from '../fixtures.js';

export default {
  title: 'Domain/MarqueeMatchups',
  component: MarqueeMatchups,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => <div style={{ maxWidth: 900 }}><MarqueeMatchups scoreboard={nationalScoreboard} /></div>,
};
export const ThreeGames = {
  render: () => <div style={{ maxWidth: 900 }}><MarqueeMatchups scoreboard={nationalScoreboard} limit={3} /></div>,
};
export const Empty = {
  render: () => <MarqueeMatchups scoreboard={[]} />,
};

import NextGameCard from './NextGameCard.jsx';
import { nextGame } from '../fixtures.js';

export default {
  title: 'Domain/NextGameCard',
  component: NextGameCard,
  parameters: { layout: 'centered' },
};

export const Default = { render: () => <div style={{ width: 340 }}><NextGameCard game={nextGame} /></div> };
export const Unranked = {
  render: () => <div style={{ width: 340 }}><NextGameCard game={{ ...nextGame, opponent: 'Wisconsin Badgers', opponent_abbr: 'WIS', opponent_espn_id: 275, opponent_rank: null, home: false }} /></div>,
};

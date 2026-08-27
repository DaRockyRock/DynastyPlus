import BettingCard from './BettingCard.jsx';
import { betting } from '../fixtures.js';

export default { title: 'Domain/BettingCard', component: BettingCard, parameters: { layout: 'padded' } };

export const GameAndFutures = { render: () => <div style={{ width: 340 }}><BettingCard betting={betting} /></div> };
export const FuturesOnly = {
  render: () => <div style={{ width: 340 }}><BettingCard betting={{ game: null, futures: betting.futures }} /></div>,
};

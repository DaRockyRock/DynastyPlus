import RumorCard from './RumorCard.jsx';
import { rumor } from '../fixtures.js';

export default {
  title: 'Domain/RumorCard',
  component: RumorCard,
  parameters: { layout: 'padded' },
};

export const ExpectedToEnter = { render: () => <div style={{ width: 460 }}><RumorCard rumor={rumor} /></div> };
export const CommittedIn = {
  render: () => <div style={{ width: 460 }}><RumorCard rumor={{ ...rumor, player: 'Reggie Stallworth', position: 'WR', team: 'Arizona State Sun Devils', status: 'Committed in', confidence: 95, detail: 'Already enrolled and pushing for a starting role.' }} /></div>,
};

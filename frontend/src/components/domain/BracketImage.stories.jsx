import BracketImage from './BracketImage.jsx';
import { committeeBallot } from '../fixtures.js';

const seeds = {};
committeeBallot.forEach((t) => { seeds[t.rank] = t; });

export default {
  title: 'Domain/BracketImage',
  component: BracketImage,
  parameters: { layout: 'padded' },
};

export const SeededField = {
  render: () => <div style={{ width: 820 }}><BracketImage seeds={seeds} /></div>,
};

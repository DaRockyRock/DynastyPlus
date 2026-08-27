import PlayoffBracket, { SeedRow } from './PlayoffBracket.jsx';
import { bracket } from '../fixtures.js';

export default {
  title: 'Domain/PlayoffBracket',
  component: PlayoffBracket,
  parameters: { layout: 'padded' },
};

export const Default = { render: () => <div style={{ width: 760 }}><PlayoffBracket bracket={bracket} /></div> };

export const SingleSeed = {
  render: () => <div style={{ width: 360 }}><SeedRow seed={bracket.byes[0]} bye /></div>,
};

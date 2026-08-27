import CrystalBallCard from './CrystalBallCard.jsx';
import { crystalBall } from '../fixtures.js';

export default {
  title: 'Domain/CrystalBallCard',
  component: CrystalBallCard,
  parameters: { layout: 'padded' },
};

export const HighConfidence = { render: () => <div style={{ width: 440 }}><CrystalBallCard pick={crystalBall} /></div> };
export const Coinflip = {
  render: () => <div style={{ width: 440 }}><CrystalBallCard pick={{ ...crystalBall, confidence: 5, prediction: 'Oregon Ducks' }} /></div>,
};

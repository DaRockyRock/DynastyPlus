import PlayoffBracket from './PlayoffBracket.jsx';
import {
  playoffBracket12, playoffBracket12Played, playoffBracket24,
  playoffBracket11DoubleBye, playoffBracket2, playoffBracket1,
} from '../fixtures.js';

export default {
  title: 'Domain/PlayoffBracket',
  component: PlayoffBracket,
  parameters: { layout: 'padded' },
};

const frame = (bracket, props = {}) => (
  <div style={{ maxWidth: 1200 }}>
    <PlayoffBracket bracket={bracket} championLabel="2026 National Champion" {...props} />
  </div>
);

export const TwelveTeamCFP = { render: () => frame(playoffBracket12, { userTeamId: 158 }) };
export const FirstRoundPlayed = { render: () => frame(playoffBracket12Played, { userTeamId: 158 }) };
export const TwentyFourTeams = { render: () => frame(playoffBracket24) };
export const DoubleByeEleven = { render: () => frame(playoffBracket11DoubleBye) };
export const BcsTitleGame = { render: () => frame(playoffBracket2) };
export const PollEraChampion = { render: () => frame(playoffBracket1) };

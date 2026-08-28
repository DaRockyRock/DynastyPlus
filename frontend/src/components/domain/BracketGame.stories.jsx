import BracketGame from './BracketGame.jsx';
import { playoffBracket12, playoffBracket12Played } from '../fixtures.js';

export default {
  title: 'Domain/BracketGame',
  component: BracketGame,
};

const frame = (game, props = {}) => (
  <div style={{ width: 236 }}><BracketGame game={game} {...props} /></div>
);

export const CampusFirstRound = { render: () => frame(playoffBracket12.rounds[0].games[0], { userTeamId: 158 }) };
export const BowlQuarterfinal = { render: () => frame(playoffBracket12.rounds[1].games[0]) };
export const AwaitingWinner = { render: () => frame(playoffBracket12.rounds[2].games[0]) };
export const FinalScore = { render: () => frame(playoffBracket12Played.rounds[0].games[0]) };
export const Championship = { render: () => frame(playoffBracket12.rounds[3].games[0], { final: true }) };

// A reseeded format's later round before the previous round is final: the
// matchup is a pair of labeled placeholders until the survivors re-pair.
export const ReseededPlaceholder = {
  render: () => frame({
    id: 'R2G1',
    round: 2,
    slots: [
      { type: 'reseed', label: 'No. 1 seed left' },
      { type: 'reseed', label: 'No. 8 seed left' },
    ],
    site: { type: 'campus', venue: "Higher seed's stadium", city: 'Campus site', bowl: null, host_espn_id: null },
    status: 'scheduled',
    winner: null,
    scores: null,
  }),
};

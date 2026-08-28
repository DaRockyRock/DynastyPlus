import PlayoffSelectionSummary from './PlayoffSelectionSummary.jsx';
import { playoffTeams } from '../fixtures.js';

export default {
  title: 'Domain/PlayoffSelectionSummary',
  component: PlayoffSelectionSummary,
};

const selection = {
  auto_bids: [
    { ...playoffTeams[0], seed: 1 },
    { ...playoffTeams[6], seed: 7 },
    { ...playoffTeams[13], seed: 12 },
  ],
  excluded: [
    { ...playoffTeams[8], reason: 'More than 2 losses' },
    { ...playoffTeams[10], reason: 'Lost on rivalry week' },
  ],
  first_out: [playoffTeams[12], playoffTeams[14]],
  notes: ['Notre Dame is guaranteed a bid under its independent access rule'],
};

export const FullSummary = {
  render: () => <div style={{ width: 460 }}><PlayoffSelectionSummary selection={selection} /></div>,
};
export const NotesOnly = {
  render: () => <div style={{ width: 460 }}><PlayoffSelectionSummary selection={{ notes: ['Only 10 eligible teams are known; the field is short of 12'] }} /></div>,
};

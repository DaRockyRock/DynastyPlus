import ResultCard from './ResultCard.jsx';
import { lastResult } from '../fixtures.js';

export default {
  title: 'Domain/ResultCard',
  component: ResultCard,
  parameters: { layout: 'centered' },
};

export const Win = { render: () => <div style={{ width: 340 }}><ResultCard result={lastResult} /></div> };
export const Loss = {
  render: () => <div style={{ width: 340 }}><ResultCard result={{ ...lastResult, result: 'L', score: '20-23', opponent: 'Minnesota Golden Gophers', opponent_abbr: 'MINN', opponent_espn_id: 135, rank_matchup: null }} /></div>,
};

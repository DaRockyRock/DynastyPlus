import RankCardGrid from './RankCardGrid.jsx';
import { pollEntries, pollEntriesTricky } from '../fixtures.js';

export default {
  title: 'Domain/RankCardGrid',
  component: RankCardGrid,
};

export const Top12 = {
  args: {
    entries: pollEntries,
    userTeam: 'Nebraska Cornhuskers',
    onOpen: () => {},
    onCompare: () => {},
  },
};

export const WithComparisonPins = {
  args: {
    entries: pollEntries,
    userTeam: 'Nebraska Cornhuskers',
    comparedRows: [12, 5],
    onOpen: () => {},
    onCompare: () => {},
  },
};

// Long school names and long conference names must all show without collapsing.
export const LongNames = {
  args: {
    entries: pollEntriesTricky,
    userTeam: 'New Mexico Lobos',
    onOpen: () => {},
    onCompare: () => {},
  },
};

export const Empty = { args: { entries: [] } };

import ResumeGameRow from './ResumeGameRow.jsx';
import { teamResume } from '../fixtures.js';

export default {
  title: 'Domain/ResumeGameRow',
  component: ResumeGameRow,
};

export const RankedWin = { args: { game: teamResume.games[2] } };
export const NeutralSiteWin = { args: { game: teamResume.games[1] } };
export const Loss = { args: { game: teamResume.games[3] } };
export const Compact = { args: { game: teamResume.best_wins[0], compact: true } };
export const Upcoming = { args: { game: teamResume.upcoming[1] } };

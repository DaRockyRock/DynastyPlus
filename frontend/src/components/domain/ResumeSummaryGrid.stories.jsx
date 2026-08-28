import ResumeSummaryGrid from './ResumeSummaryGrid.jsx';
import { teamResume } from '../fixtures.js';

export default {
  title: 'Domain/ResumeSummaryGrid',
  component: ResumeSummaryGrid,
};

export const Default = { args: { summary: teamResume.summary } };
export const NegativeMargin = {
  args: { summary: { ...teamResume.summary, avg_margin: -6.4, ppg: 18.2, papg: 24.6 } },
};

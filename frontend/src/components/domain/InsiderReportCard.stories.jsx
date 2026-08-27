import InsiderReportCard from './InsiderReportCard.jsx';
import { insiderReport } from '../fixtures.js';

export default {
  title: 'Domain/InsiderReportCard',
  component: InsiderReportCard,
  parameters: { layout: 'padded' },
};

export const Developing = { render: () => <div style={{ width: 560 }}><InsiderReportCard report={insiderReport} /></div> };
export const Corroborated = {
  render: () => <div style={{ width: 560 }}><InsiderReportCard report={{ ...insiderReport, status: 'corroborated', credibility: 93, reporter: 'Dana Reyes', outlet: 'The Press Box' }} /></div>,
};
export const Disputed = {
  render: () => <div style={{ width: 560 }}><InsiderReportCard report={{ ...insiderReport, status: 'disputed', confidence: 35 }} /></div>,
};

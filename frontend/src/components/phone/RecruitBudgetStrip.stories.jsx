import RecruitBudgetStrip from './RecruitBudgetStrip.jsx';
import { budgetSnapshot } from '../fixtures.js';

export default {
  title: 'Phone/RecruitBudgetStrip',
  component: RecruitBudgetStrip,
  parameters: { layout: 'fullscreen' },
};

const Frame = ({ children }) => (
  <div style={{ background: '#000', padding: 16, width: 380, fontFamily: 'var(--font-body)' }}>{children}</div>
);

export const Default = { render: () => <Frame><RecruitBudgetStrip snapshot={budgetSnapshot} /></Frame> };

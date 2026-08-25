import BudgetSummaryBar from './BudgetSummaryBar.jsx';
import { budgetSnapshot } from '../fixtures.js';

export default {
  title: 'Domain/BudgetSummaryBar',
  component: BudgetSummaryBar,
  parameters: { layout: 'padded' },
};

export const Full = { render: () => <BudgetSummaryBar snapshot={budgetSnapshot} /> };
export const Compact = { render: () => <BudgetSummaryBar snapshot={budgetSnapshot} compact /> };

import RosterNilTable from './RosterNilTable.jsx';
import { budgetSnapshot } from '../fixtures.js';

export default {
  title: 'Domain/RosterNilTable',
  component: RosterNilTable,
  parameters: { layout: 'padded' },
};

export const Retention = {
  render: () => <RosterNilTable rows={budgetSnapshot.roster_nil} onOffer={() => {}} />,
};

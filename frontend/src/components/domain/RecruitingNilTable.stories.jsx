import RecruitingNilTable from './RecruitingNilTable.jsx';
import { budgetSnapshot } from '../fixtures.js';

export default {
  title: 'Domain/RecruitingNilTable',
  component: RecruitingNilTable,
  parameters: { layout: 'padded' },
};

export const Board = {
  render: () => <RecruitingNilTable rows={budgetSnapshot.recruiting_nil} onOffer={() => {}} />,
};

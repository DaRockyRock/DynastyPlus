import RecruitRow from './RecruitRow.jsx';
import { recruitRows } from '../fixtures.js';

export default {
  title: 'Domain/RecruitRow',
  component: RecruitRow,
  parameters: { layout: 'padded' },
};

export const Committed = { render: () => <div style={{ width: 720 }}><RecruitRow recruit={recruitRows[0]} /></div> };
export const Uncommitted = { render: () => <div style={{ width: 720 }}><RecruitRow recruit={recruitRows[1]} /></div> };
export const Signed = { render: () => <div style={{ width: 720 }}><RecruitRow recruit={recruitRows[2]} /></div> };

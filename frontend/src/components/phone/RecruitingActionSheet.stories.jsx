import RecruitingActionSheet from './RecruitingActionSheet.jsx';
import { recruitingActions } from '../fixtures.js';

export default {
  title: 'Phone/RecruitingActionSheet',
  component: RecruitingActionSheet,
  parameters: { layout: 'fullscreen' },
};

const Frame = ({ children }) => (
  <div style={{ background: '#000', width: 380, height: 560, position: 'relative', fontFamily: 'var(--font-body)' }}>{children}</div>
);

export const FullHours = { render: () => <Frame><RecruitingActionSheet actions={recruitingActions} hoursRemaining={1500} onPick={() => {}} onClose={() => {}} /></Frame> };
export const LowHours = { render: () => <Frame><RecruitingActionSheet actions={recruitingActions} hoursRemaining={180} onPick={() => {}} onClose={() => {}} /></Frame> };

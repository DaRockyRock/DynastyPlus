import ChatActionBar from './ChatActionBar.jsx';
import { recruitMarker, playerMarker, budgetMarker } from '../fixtures.js';

export default {
  title: 'Phone/ChatActionBar',
  component: ChatActionBar,
  parameters: { layout: 'fullscreen' },
};

const Frame = ({ children }) => (
  <div style={{ background: '#000', padding: 16, width: 380, fontFamily: 'var(--font-body)' }}>{children}</div>
);

export const Recruit = { render: () => <Frame><ChatActionBar marker={recruitMarker} onOffer={() => {}} onRecruitingAction={() => {}} /></Frame> };
export const Player = { render: () => <Frame><ChatActionBar marker={playerMarker} onOffer={() => {}} /></Frame> };
export const AthleticDirector = { render: () => <Frame><ChatActionBar marker={budgetMarker} onBudgetRequest={() => {}} /></Frame> };

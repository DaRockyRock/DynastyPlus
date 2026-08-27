import ChatBudgetHeader from './ChatBudgetHeader.jsx';
import { recruitMarker, playerMarker, budgetMarker } from '../fixtures.js';

export default {
  title: 'Phone/ChatBudgetHeader',
  component: ChatBudgetHeader,
  parameters: { layout: 'fullscreen' },
};

const Frame = ({ children }) => (
  <div style={{ background: '#000', padding: 16, width: 380, fontFamily: 'var(--font-body)' }}>{children}</div>
);

export const Recruit = { render: () => <Frame><ChatBudgetHeader marker={recruitMarker} /></Frame> };
export const Player = { render: () => <Frame><ChatBudgetHeader marker={{ ...playerMarker, risk_of_leaving: 58 }} /></Frame> };
export const AthleticDirector = { render: () => <Frame><ChatBudgetHeader marker={budgetMarker} /></Frame> };
export const Staff = { render: () => <Frame><ChatBudgetHeader marker={{ kind: 'staff', hours_remaining: 900, hours_total: 1500 }} /></Frame> };

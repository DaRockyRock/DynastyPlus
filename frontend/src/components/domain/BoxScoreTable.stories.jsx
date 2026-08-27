import BoxScoreTable from './BoxScoreTable.jsx';
import { gameCenter } from '../fixtures.js';

export default { title: 'Domain/BoxScoreTable', component: BoxScoreTable, parameters: { layout: 'padded' } };

export const UserTeam = { render: () => <div style={{ maxWidth: 560 }}><BoxScoreTable box={gameCenter.box.home} isUser /></div> };
export const Opponent = { render: () => <div style={{ maxWidth: 560 }}><BoxScoreTable box={gameCenter.box.away} /></div> };

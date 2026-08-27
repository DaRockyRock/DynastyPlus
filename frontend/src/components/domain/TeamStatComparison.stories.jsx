import TeamStatComparison from './TeamStatComparison.jsx';
import { gameCenter } from '../fixtures.js';

export default { title: 'Domain/TeamStatComparison', component: TeamStatComparison, parameters: { layout: 'padded' } };

export const Default = { render: () => <div style={{ maxWidth: 460 }}><TeamStatComparison game={gameCenter} /></div> };

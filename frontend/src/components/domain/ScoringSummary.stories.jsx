import ScoringSummary from './ScoringSummary.jsx';
import { gameCenter } from '../fixtures.js';

export default { title: 'Domain/ScoringSummary', component: ScoringSummary, parameters: { layout: 'padded' } };

export const Default = { render: () => <div style={{ maxWidth: 520 }}><ScoringSummary scoring={gameCenter.scoring_summary} /></div> };

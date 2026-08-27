import DriveChart from './DriveChart.jsx';
import { gameCenter } from '../fixtures.js';

export default { title: 'Domain/DriveChart', component: DriveChart, parameters: { layout: 'padded' } };

export const Default = { render: () => <div style={{ maxWidth: 520 }}><DriveChart drives={gameCenter.drives} /></div> };

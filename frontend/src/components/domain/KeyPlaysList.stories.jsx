import KeyPlaysList from './KeyPlaysList.jsx';
import { gameCenter } from '../fixtures.js';

export default { title: 'Domain/KeyPlaysList', component: KeyPlaysList, parameters: { layout: 'padded' } };

export const Default = { render: () => <div style={{ maxWidth: 520 }}><KeyPlaysList plays={gameCenter.key_plays} /></div> };

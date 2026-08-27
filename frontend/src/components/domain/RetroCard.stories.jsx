import RetroCard from './RetroCard.jsx';
import { retro } from '../fixtures.js';

export default { title: 'Domain/RetroCard', component: RetroCard, parameters: { layout: 'padded' } };

export const Default = { render: () => <div style={{ width: 520 }}><RetroCard retro={retro} /></div> };

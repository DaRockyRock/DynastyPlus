import LegacyCard from './LegacyCard.jsx';
import { legacy } from '../fixtures.js';

export default { title: 'Domain/LegacyCard', component: LegacyCard, parameters: { layout: 'padded' } };

export const Default = { render: () => <div style={{ width: 480 }}><LegacyCard player={legacy} /></div> };

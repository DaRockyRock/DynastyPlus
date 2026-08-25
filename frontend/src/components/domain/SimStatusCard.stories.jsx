import SimStatusCard from './SimStatusCard.jsx';
import { simStatus } from '../fixtures.js';

export default {
  title: 'Domain/SimStatusCard',
  component: SimStatusCard,
  parameters: { layout: 'padded' },
};

export const Default = { render: () => <div style={{ width: 760 }}><SimStatusCard status={simStatus} /></div> };

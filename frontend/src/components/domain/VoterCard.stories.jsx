import VoterCard from './VoterCard.jsx';
import { voter } from '../fixtures.js';

export default {
  title: 'Domain/VoterCard',
  component: VoterCard,
  parameters: { layout: 'centered' },
};

export const Default = { render: () => <div style={{ width: 300 }}><VoterCard voter={voter} /></div> };

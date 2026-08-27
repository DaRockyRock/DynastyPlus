import VisitCard from './VisitCard.jsx';
import { visit } from '../fixtures.js';

export default {
  title: 'Domain/VisitCard',
  component: VisitCard,
  parameters: { layout: 'padded' },
};

export const Default = { render: () => <div style={{ width: 440 }}><VisitCard visit={visit} /></div> };

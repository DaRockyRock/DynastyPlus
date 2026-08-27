import CandidateCard from './CandidateCard.jsx';
import { candidate } from '../fixtures.js';

export default {
  title: 'Domain/CandidateCard',
  component: CandidateCard,
  parameters: { layout: 'padded' },
};

export const Default = { render: () => <div style={{ width: 460 }}><CandidateCard candidate={candidate} /></div> };
export const G5Winner = {
  render: () => <div style={{ width: 460 }}><CandidateCard candidate={{ name: 'Tobias Frame', current: 'Group of Five HC', archetype: 'Proven G5 winner', fit: 88, why: 'Back-to-back conference titles and an elite portal-evaluation track record.' }} /></div>,
};

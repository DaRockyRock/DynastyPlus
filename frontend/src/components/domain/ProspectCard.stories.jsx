import ProspectCard from './ProspectCard.jsx';
import { prospect } from '../fixtures.js';

export default {
  title: 'Domain/ProspectCard',
  component: ProspectCard,
  parameters: { layout: 'padded' },
};

export const Target = { render: () => <div style={{ width: 420 }}><ProspectCard prospect={prospect} /></div> };
export const Commit = {
  render: () => <div style={{ width: 420 }}><ProspectCard committed prospect={{ ...prospect, name: 'Jordan Eaves', position: 'QB', stars: 4, rating: 0.9412, hometown: 'Frisco, TX', leader: undefined, predicted: undefined, visit: undefined }} /></div>,
};
export const WithBudget = {
  render: () => (
    <div style={{ width: 420 }}>
      <ProspectCard
        prospect={prospect}
        budget={{ id: 'cam_brooks_lee', name: 'Cam Brooks-Lee', expected_nil: 450000, offer: 600000, interest: 81, stage: 'Verbal', dealbreaker: 'Brand Exposure' }}
      />
    </div>
  ),
};

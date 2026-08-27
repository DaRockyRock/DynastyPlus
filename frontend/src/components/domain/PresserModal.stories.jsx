import PresserModal from './PresserModal.jsx';
import { presser, presserComplete } from '../fixtures.js';

export default { title: 'Domain/PresserModal', component: PresserModal, parameters: { layout: 'fullscreen' } };

export const InProgress = {
  render: () => <PresserModal presser={presser} coachName="Garrett Mason" onAnswer={(t) => alert(t)} onSkip={() => alert('skip')} />,
};
// After the coach hits Respond: the busy scrim covers the card while the next
// question generates (the model can take several seconds), so the modal never
// looks frozen on the question just answered.
export const Generating = {
  render: () => <PresserModal presser={presser} coachName="Garrett Mason" busy onAnswer={(t) => alert(t)} onSkip={() => alert('skip')} />,
};
export const Complete = {
  render: () => <PresserModal presser={presserComplete} coachName="Garrett Mason" onClose={() => alert('continue')} />,
};

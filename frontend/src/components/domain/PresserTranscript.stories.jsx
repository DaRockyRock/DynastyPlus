import PresserTranscript from './PresserTranscript.jsx';
import { presserComplete } from '../fixtures.js';

export default { title: 'Domain/PresserTranscript', component: PresserTranscript, parameters: { layout: 'padded' } };

export const Default = {
  render: () => <div style={{ maxWidth: 560 }}><PresserTranscript turns={presserComplete.turns} coachName="Garrett Mason" /></div>,
};

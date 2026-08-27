import PresserAnswerInput from './PresserAnswerInput.jsx';

export default { title: 'Domain/PresserAnswerInput', component: PresserAnswerInput, parameters: { layout: 'padded' } };

export const Default = {
  render: () => <div style={{ maxWidth: 520 }}><PresserAnswerInput onSend={(t) => alert(t)} onSkip={() => alert('skip')} /></div>,
};
export const Busy = {
  render: () => <div style={{ maxWidth: 520 }}><PresserAnswerInput busy /></div>,
};

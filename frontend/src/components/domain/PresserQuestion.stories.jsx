import PresserQuestion from './PresserQuestion.jsx';

export default { title: 'Domain/PresserQuestion', component: PresserQuestion, parameters: { layout: 'padded' } };

export const Question = {
  render: () => <div style={{ maxWidth: 520 }}><PresserQuestion question="Marcus Whitfield threw for 268 and two scores. How would you assess his night?" /></div>,
};
export const FollowUp = {
  render: () => <div style={{ maxWidth: 520 }}><PresserQuestion question="Just to follow up, was that more on the protection or the reads?" followUp /></div>,
};

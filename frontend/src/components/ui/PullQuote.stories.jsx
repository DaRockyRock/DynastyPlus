import PullQuote from './PullQuote.jsx';

export default { title: 'UI/PullQuote', component: PullQuote, parameters: { layout: 'padded' } };

export const Default = {
  render: () => (
    <div style={{ width: 520 }}>
      <PullQuote>Resume beats reputation now, and this one is built to last.</PullQuote>
    </div>
  ),
};

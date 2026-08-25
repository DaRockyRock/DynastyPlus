import DealbreakerTag from './DealbreakerTag.jsx';

export default {
  title: 'UI/DealbreakerTag',
  component: DealbreakerTag,
  parameters: { layout: 'padded' },
};

export const Examples = {
  render: () => (
    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
      {['Brand Exposure', 'Playing Time', 'Proximity to Home', 'Development', 'NFL Readiness'].map((d) => (
        <DealbreakerTag key={d} value={d} />
      ))}
    </div>
  ),
};

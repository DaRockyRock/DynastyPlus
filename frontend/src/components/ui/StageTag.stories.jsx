import StageTag from './StageTag.jsx';

export default {
  title: 'UI/StageTag',
  component: StageTag,
  parameters: { layout: 'padded' },
};

export const Funnel = {
  render: () => (
    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
      {['Open', 'Top 5', 'Top 3', 'Verbal', 'Hard Commit'].map((s) => <StageTag key={s} stage={s} />)}
    </div>
  ),
};

import PointsValue from './PointsValue.jsx';

export default {
  title: 'UI/PointsValue',
  component: PointsValue,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => (
    <div style={{ display: 'flex', gap: 22, alignItems: 'baseline', fontSize: 22 }}>
      <PointsValue value={12000} />
      <PointsValue value={3140} tone="pos" />
      <PointsValue value={-120} tone="neg" />
    </div>
  ),
};

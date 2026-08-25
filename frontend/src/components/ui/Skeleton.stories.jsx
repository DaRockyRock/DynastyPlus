import Skeleton from './Skeleton.jsx';

export default {
  title: 'UI/Skeleton',
  component: Skeleton,
  parameters: { layout: 'padded' },
};

export const Block = { args: { height: 240 } };
export const Lines = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: 420 }}>
      <Skeleton height={28} />
      <Skeleton height={16} />
      <Skeleton height={16} />
    </div>
  ),
};

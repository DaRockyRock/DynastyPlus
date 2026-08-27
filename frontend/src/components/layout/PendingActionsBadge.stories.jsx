import PendingActionsBadge from './PendingActionsBadge.jsx';

export default {
  title: 'Layout/PendingActionsBadge',
  component: PendingActionsBadge,
  parameters: { layout: 'centered' },
};

export const None = { render: () => <PendingActionsBadge count={0} /> };
export const One = { render: () => <PendingActionsBadge count={1} /> };
export const Several = { render: () => <PendingActionsBadge count={4} onClick={() => {}} /> };

import CountBadge from './CountBadge.jsx';

export default {
  title: 'UI/CountBadge',
  component: CountBadge,
  parameters: { layout: 'centered' },
};

// Sits on top of an action button, so show it anchored to one.
const Host = ({ count }) => (
  <span style={{ position: 'relative', display: 'inline-flex' }}>
    <button className="icon-btn accent">Phone</button>
    <CountBadge count={count} />
  </span>
);

export const One = { render: () => <Host count={1} /> };
export const Several = { render: () => <Host count={4} /> };
export const Overflow = { render: () => <Host count={142} /> };
export const Zero = { render: () => <Host count={0} /> };

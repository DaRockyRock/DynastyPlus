import EmptyState from './EmptyState.jsx';

export default {
  title: 'UI/EmptyState',
  component: EmptyState,
  parameters: { layout: 'padded' },
};

export const Default = { render: () => <div style={{ width: 420 }}><EmptyState /></div> };
export const Custom = { render: () => <div style={{ width: 420 }}><EmptyState>Quiet on the portal for now.</EmptyState></div> };

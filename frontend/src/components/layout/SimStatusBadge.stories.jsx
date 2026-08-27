import SimStatusBadge from './SimStatusBadge.jsx';

export default {
  title: 'Layout/SimStatusBadge',
  component: SimStatusBadge,
  parameters: { layout: 'padded' },
};

export const Default = { render: () => <SimStatusBadge week={5} /> };

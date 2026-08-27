import UnreadDot from './UnreadDot.jsx';

export default {
  title: 'Phone/UnreadDot',
  component: UnreadDot,
  parameters: { layout: 'centered', backgrounds: { default: 'dark' } },
};

export const Unread = { render: () => <UnreadDot unread /> };
export const Read = { render: () => <UnreadDot unread={false} /> };

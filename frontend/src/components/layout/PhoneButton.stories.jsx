import PhoneButton from './PhoneButton.jsx';

export default {
  title: 'Layout/PhoneButton',
  component: PhoneButton,
  parameters: { layout: 'centered' },
};

export const NoUnread = { render: () => <PhoneButton count={0} /> };
export const WithUnread = { render: () => <PhoneButton count={3} /> };
export const Overflow = { render: () => <PhoneButton count={120} /> };

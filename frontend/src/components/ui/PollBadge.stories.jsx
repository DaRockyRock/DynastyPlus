import PollBadge from './PollBadge.jsx';

export default {
  title: 'UI/PollBadge',
  component: PollBadge,
};

export const CFP = { args: { poll: 'cfp', size: 48 } };
export const AP = { args: { poll: 'ap', size: 48 } };

export const Lockups = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <PollBadge poll="cfp" size={34} lockup />
      <PollBadge poll="ap" size={34} lockup />
    </div>
  ),
};

export const Sizes = {
  render: () => (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 14 }}>
      <PollBadge poll="cfp" size={16} />
      <PollBadge poll="cfp" size={24} />
      <PollBadge poll="cfp" size={40} />
      <PollBadge poll="cfp" size={64} />
      <PollBadge poll="ap" size={16} />
      <PollBadge poll="ap" size={24} />
      <PollBadge poll="ap" size={40} />
      <PollBadge poll="ap" size={64} />
    </div>
  ),
};

import Avatar from './Avatar.jsx';

export default {
  title: 'UI/Avatar',
  component: Avatar,
  parameters: { layout: 'centered' },
};

export const FromName = { args: { name: 'Garrett Mason', size: 48 } };
export const Gradient = { args: { name: 'Cam Brooks-Lee', size: 48, gradient: true } };
export const Sizes = {
  render: () => (
    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
      {[32, 40, 56].map((s) => <Avatar key={s} name="Dana Reyes" size={s} />)}
    </div>
  ),
};

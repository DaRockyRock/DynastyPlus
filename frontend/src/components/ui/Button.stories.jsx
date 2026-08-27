import Button from './Button.jsx';
import { PlayIcon, PhoneIcon, RefreshIcon } from './icons.jsx';

export default {
  title: 'UI/Button',
  component: Button,
  parameters: { layout: 'centered' },
  argTypes: {
    variant: { control: 'select', options: ['action', 'accent', 'regen'] },
    spinning: { control: 'boolean' },
  },
};

export const Action = { args: { variant: 'action', children: 'Advance Week', icon: <PlayIcon /> } };
export const Accent = { args: { variant: 'accent', children: 'Phone', icon: <PhoneIcon /> } };
export const Regenerate = { args: { variant: 'regen', children: 'Regenerate', icon: <RefreshIcon size={14} /> } };
export const Spinning = { args: { variant: 'regen', children: 'Regenerate', icon: <RefreshIcon size={14} />, spinning: true } };
export const Disabled = { args: { variant: 'action', children: 'Unavailable', disabled: true } };

export const AllVariants = {
  render: () => (
    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
      <Button variant="action" icon={<PlayIcon />}>Advance Week</Button>
      <Button variant="accent" icon={<PhoneIcon />}>Phone</Button>
      <Button variant="regen" icon={<RefreshIcon size={14} />}>Regenerate</Button>
    </div>
  ),
};

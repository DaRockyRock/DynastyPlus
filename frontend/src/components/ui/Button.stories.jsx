import Button from './Button.jsx';
import { PlayIcon, RefreshIcon } from './icons.jsx';

export default {
  title: 'UI/Button',
  component: Button,
  parameters: { layout: 'centered' },
  argTypes: {
    variant: { control: 'select', options: ['action', 'accent', 'compact'] },
    spinning: { control: 'boolean' },
  },
};

export const Action = { args: { variant: 'action', children: 'Advance Week', icon: <PlayIcon /> } };
export const Accent = { args: { variant: 'accent', children: 'Start Season', icon: <PlayIcon /> } };
export const Compact = { args: { variant: 'compact', children: 'Reset', icon: <RefreshIcon size={14} /> } };
export const Spinning = { args: { variant: 'accent', children: 'Simulating', icon: <RefreshIcon size={14} />, spinning: true } };
export const Disabled = { args: { variant: 'action', children: 'Unavailable', disabled: true } };

export const AllVariants = {
  render: () => (
    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
      <Button variant="action" icon={<PlayIcon />}>Advance Week</Button>
      <Button variant="accent" icon={<PlayIcon />}>Start Season</Button>
      <Button variant="compact" icon={<RefreshIcon size={14} />}>Reset</Button>
    </div>
  ),
};

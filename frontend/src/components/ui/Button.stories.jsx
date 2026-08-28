import Button from './Button.jsx';
import { PlayIcon, RefreshIcon } from './icons.jsx';

export default {
  title: 'UI/Button',
  component: Button,
  parameters: { layout: 'centered' },
  argTypes: {
    variant: { control: 'select', options: ['action', 'accent', 'regen'] },
    spinning: { control: 'boolean' },
  },
};

export const Action = { args: { variant: 'action', children: 'Generate Schedule', icon: <PlayIcon /> } };
export const Accent = { args: { variant: 'accent', children: 'Update Dynasty File', icon: <PlayIcon /> } };
export const Regenerate = { args: { variant: 'regen', children: 'Scan Saves', icon: <RefreshIcon size={14} /> } };
export const Spinning = { args: { variant: 'regen', children: 'Scanning', icon: <RefreshIcon size={14} />, spinning: true } };
export const Disabled = { args: { variant: 'action', children: 'Unavailable', disabled: true } };

export const AllVariants = {
  render: () => (
    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
      <Button variant="action" icon={<PlayIcon />}>Generate Schedule</Button>
      <Button variant="accent" icon={<PlayIcon />}>Update Dynasty File</Button>
      <Button variant="regen" icon={<RefreshIcon size={14} />}>Scan Saves</Button>
    </div>
  ),
};

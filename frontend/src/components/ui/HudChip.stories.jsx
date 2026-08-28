import HudChip from './HudChip.jsx';
import { CheckIcon, AlertIcon } from './icons.jsx';

export default {
  title: 'UI/HudChip',
  component: HudChip,
};

export const Ready = {
  args: {
    icon: <CheckIcon />,
    label: 'Schedule',
    value: 'Ready',
    accent: 'var(--recruiting)',
  },
};

export const NeedsWork = {
  args: {
    icon: <AlertIcon />,
    label: 'Conflicts',
    value: '2',
    accent: 'var(--accent-orange)',
  },
};

export const Row = {
  render: () => (
    <div style={{ display: 'flex', gap: 8 }}>
      <HudChip icon={<CheckIcon />} label="Teams" value="136" accent="var(--recruiting)" />
      <HudChip icon={<AlertIcon />} label="Conflicts" value="2" accent="var(--accent-orange)" />
    </div>
  ),
};

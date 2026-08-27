import SettingsIcon from './SettingsIcon.jsx';

export default {
  title: 'Settings/SettingsIcon',
  component: SettingsIcon,
  parameters: { layout: 'padded' },
};

const NAMES = [
  'shield', 'whistle', 'chart', 'swords', 'clipboard', 'jersey', 'star', 'target',
  'newspaper', 'mic', 'binoculars', 'ballot', 'phone', 'gavel', 'fire', 'users',
  'trophy', 'arrow-in', 'arrow-out', 'unknown',
];

export const All = {
  render: () => (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 18 }}>
      {NAMES.map((n) => (
        <div key={n} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, color: 'var(--chalk-2)' }}>
          <SettingsIcon name={n} size={24} />
          <span style={{ fontSize: 11, color: 'var(--chalk-3)' }}>{n}</span>
        </div>
      ))}
    </div>
  ),
};

import * as Icons from './icons.jsx';

export default {
  title: 'UI/Icons',
  parameters: { layout: 'centered' },
};

export const AllIcons = {
  render: () => (
    <div style={{ display: 'flex', gap: 24, color: 'var(--text)' }}>
      {Object.entries(Icons).map(([name, Icon]) => (
        <div key={name} style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-3)' }}>
          <Icon size={26} />
          <div style={{ marginTop: 8 }}>{name}</div>
        </div>
      ))}
    </div>
  ),
};

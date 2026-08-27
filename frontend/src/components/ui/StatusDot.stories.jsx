import StatusDot from './StatusDot.jsx';

export default {
  title: 'UI/StatusDot',
  component: StatusDot,
  parameters: { layout: 'centered' },
};

export const AllTones = {
  render: () => (
    <div style={{ display: 'flex', gap: 22, alignItems: 'center' }}>
      {['live', 'idle', 'off', 'error'].map((t) => (
        <span key={t} style={{ display: 'inline-flex', gap: 8, alignItems: 'center', color: '#a4b1c2', fontSize: 13 }}>
          <StatusDot tone={t} pulse={t === 'live'} /> {t}
        </span>
      ))}
    </div>
  ),
};

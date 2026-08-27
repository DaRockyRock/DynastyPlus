import Badge from './Badge.jsx';

export default {
  title: 'UI/Badge',
  component: Badge,
  parameters: { layout: 'centered' },
};

export const Week = { args: { variant: 'week', children: 'Week 10' } };
export const Season = { args: { label: '2026' } };
export const CFP = { args: { variant: 'rank-cfp', label: 'CFP', value: '#5' } };
export const AP = { args: { variant: 'rank-ap', label: 'AP', value: '#5' } };

export const Row = {
  render: () => (
    <div style={{ display: 'flex', gap: 10 }}>
      <Badge variant="week">Week 10</Badge>
      <Badge label="2026" />
      <Badge variant="rank-cfp" label="CFP" value="#5" />
      <Badge variant="rank-ap" label="AP" value="#5" />
    </div>
  ),
};

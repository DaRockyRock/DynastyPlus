import ReliabilityBar from './ReliabilityBar.jsx';

export default {
  title: 'UI/ReliabilityBar',
  component: ReliabilityBar,
  parameters: { layout: 'centered' },
  argTypes: { score: { control: { type: 'range', min: 0, max: 100 } } },
};

export const High = { args: { score: 93 } };
export const Medium = { args: { score: 74 } };
export const Low = { args: { score: 58 } };

export const Scale = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {[95, 84, 70, 55, 30].map((s) => <ReliabilityBar key={s} score={s} />)}
    </div>
  ),
};

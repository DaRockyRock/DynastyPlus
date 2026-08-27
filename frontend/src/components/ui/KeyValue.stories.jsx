import KeyValue from './KeyValue.jsx';
import ReliabilityBar from './ReliabilityBar.jsx';

export default {
  title: 'UI/KeyValue',
  component: KeyValue,
  parameters: { layout: 'padded' },
};

export const Basic = {
  render: () => (
    <div className="card panel" style={{ width: 360 }}>
      <KeyValue k="The Press Box" v={<ReliabilityBar score={93} />} />
      <KeyValue k="Saturday Authority" v={<ReliabilityBar score={88} />} />
      <KeyValue k="Coaching Confidential" v={<ReliabilityBar score={66} />} />
    </div>
  ),
};

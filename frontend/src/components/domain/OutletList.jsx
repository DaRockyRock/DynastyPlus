import Card from '../ui/Card.jsx';
import KeyValue from '../ui/KeyValue.jsx';
import ReliabilityBar from '../ui/ReliabilityBar.jsx';

// Panel listing fictional outlets and their reliability scores.
export default function OutletList({ outlets = [] }) {
  return (
    <Card className="panel">
      {outlets.map((o) => (
        <KeyValue
          key={o.name}
          k={<span>{o.name}<div style={{ fontSize: 11, color: 'var(--text-3)', fontWeight: 500 }}>{o.voice}</div></span>}
          v={<ReliabilityBar score={o.reliability} />}
        />
      ))}
    </Card>
  );
}

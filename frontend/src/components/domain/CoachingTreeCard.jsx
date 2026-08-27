import Card from '../ui/Card.jsx';
import KeyValue from '../ui/KeyValue.jsx';

// Coaching-tree card: head coach plus their staff branches.
export default function CoachingTreeCard({ tree }) {
  return (
    <Card className="tile">
      <h3 style={{ fontSize: 15 }}>{tree.head_coach || ''}</h3>
      <div style={{ fontSize: 12, color: 'var(--text-3)' }}>{tree.alma_mater || ''} - {tree.tenure || ''}</div>
      {(tree.branches || []).map((b, i) => (
        <KeyValue key={i} k={b.name} v={<span style={{ fontWeight: 600, color: 'var(--text-2)' }}>{b.role}</span>} />
      ))}
    </Card>
  );
}

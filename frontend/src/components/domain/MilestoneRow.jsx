import Card from '../ui/Card.jsx';
import { noEmDash } from '../../lib/format.js';

// A dated program milestone in the dynasty archive.
export default function MilestoneRow({ milestone }) {
  const m = milestone;
  return (
    <Card className="tile" style={{ marginBottom: 10, padding: 14, display: 'flex', gap: 14, alignItems: 'center' }}>
      <div style={{ fontWeight: 850, color: 'var(--team)', fontSize: 15, minWidth: 48 }}>{m.season}</div>
      <div>
        <div style={{ fontWeight: 800, fontSize: 14 }}>{noEmDash(m.title)}</div>
        <div className="muted" style={{ marginTop: 3 }}>{noEmDash(m.detail || '')}</div>
      </div>
    </Card>
  );
}

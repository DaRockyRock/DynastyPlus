import Card from '../ui/Card.jsx';
import Badge from '../ui/Badge.jsx';
import Avatar from '../ui/Avatar.jsx';
import PersonName from '../people/PersonName.jsx';
import { noEmDash } from '../../lib/format.js';

// A coaching-search candidate with a fit score and rationale.
export default function CandidateCard({ candidate }) {
  const c = candidate;
  return (
    <Card className="tile" style={{ marginBottom: 10, padding: 14, display: 'flex', gap: 14, alignItems: 'center' }}>
      {c.image && <Avatar src={c.image} name={c.name} size={42} />}
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 22, fontWeight: 850, color: 'var(--recruiting)' }}>{c.fit ?? '-'}</div>
        <div style={{ fontSize: 10, color: 'var(--text-3)' }}>FIT</div>
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 800, display: 'flex', alignItems: 'center', gap: 8 }}>
          <PersonName name={c.name} kind="candidate" /> <Badge>{c.archetype || ''}</Badge>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-3)' }}>{c.current || ''}</div>
        <div className="muted" style={{ marginTop: 5 }}>{noEmDash(c.why || '')}</div>
      </div>
    </Card>
  );
}

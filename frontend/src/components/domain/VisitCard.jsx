import Card from '../ui/Card.jsx';
import Badge from '../ui/Badge.jsx';
import PersonName from '../people/PersonName.jsx';
import { noEmDash } from '../../lib/format.js';

// Recap of a recruit's campus visit.
export default function VisitCard({ visit }) {
  const v = visit;
  return (
    <Card className="tile" style={{ marginBottom: 10, padding: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontWeight: 800 }}>
          <PersonName name={v.prospect} kind="recruit" /> <span style={{ color: 'var(--text-3)', fontWeight: 600 }}>{v.position || ''}</span>
        </div>
        <Badge>{v.type || 'Visit'}</Badge>
      </div>
      <div style={{ fontSize: 11, color: 'var(--cfp)', marginTop: 3 }}>{v.when || ''}</div>
      <div className="muted" style={{ marginTop: 8 }}>{noEmDash(v.recap || '')}</div>
    </Card>
  );
}

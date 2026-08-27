import Card from '../ui/Card.jsx';
import Badge from '../ui/Badge.jsx';
import ReliabilityBar from '../ui/ReliabilityBar.jsx';
import PersonName from '../people/PersonName.jsx';
import { noEmDash } from '../../lib/format.js';

// Transfer-portal rumor with a status accent and confidence meter.
export default function RumorCard({ rumor }) {
  const r = rumor;
  const status = (r.status || '').toLowerCase();
  const color = status.includes('committed') ? 'var(--recruiting)'
    : status.includes('expected') ? 'var(--carousel)' : 'var(--portal)';
  return (
    <Card className="tile" style={{ marginBottom: 12, padding: 16, borderLeft: `3px solid ${color}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
        <div style={{ fontWeight: 800, fontSize: 15 }}>
          <PersonName name={r.player} kind="transfer" /> <span style={{ color: 'var(--text-3)', fontWeight: 600 }}>{r.position || ''}</span>
        </div>
        <Badge><span style={{ color }}>{r.status || ''}</span></Badge>
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>{r.team || ''}</div>
      <div className="muted" style={{ marginTop: 8 }}>{noEmDash(r.detail || '')}</div>
      {r.confidence != null && (
        <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-3)' }}>
          Confidence <ReliabilityBar score={r.confidence} />
        </div>
      )}
    </Card>
  );
}

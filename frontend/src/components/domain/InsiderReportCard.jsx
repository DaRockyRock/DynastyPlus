import Card from '../ui/Card.jsx';
import Chip from '../ui/Chip.jsx';
import StatusTag from '../ui/StatusTag.jsx';
import ReliabilityBar from '../ui/ReliabilityBar.jsx';
import PersonName from '../people/PersonName.jsx';
import { noEmDash } from '../../lib/format.js';

// Coaching-carousel insider report. Carries a tracked credibility score and a
// status (developing / corroborated / disputed) so some reports prove right
// and others do not over the season.
export default function InsiderReportCard({ report }) {
  const r = report;
  return (
    <Card style={{ padding: 16, marginBottom: 12, borderLeft: `3px solid ${r.accent || '#f59e0b'}` }}>
      <div className="a-top">
        <Chip category={r.category || 'Coaching carousel'} accent={r.accent} />
        <span style={{ marginLeft: 'auto' }}><StatusTag status={r.status} /></span>
      </div>
      <h4 style={{ margin: '0 0 6px', fontSize: 16, fontWeight: 800 }}>{noEmDash(r.headline)}</h4>
      <div className="dek">{noEmDash(r.dek || '')}</div>
      <div className="article-body">{noEmDash(r.body || '')}</div>
      <div style={{ display: 'flex', gap: 18, alignItems: 'center', marginTop: 12, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 12, color: 'var(--text-3)' }}>
          <b style={{ color: 'var(--text-2)' }}><PersonName name={r.reporter} kind="media" /></b> - {r.outlet}
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Confidence {r.confidence ?? '-'}</div>
        <div style={{ fontSize: 12, color: 'var(--text-3)', display: 'inline-flex', gap: 6, alignItems: 'center' }}>
          Credibility <ReliabilityBar score={r.credibility ?? r.reliability ?? 0} />
        </div>
      </div>
    </Card>
  );
}

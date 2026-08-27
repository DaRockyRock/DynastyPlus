import Card from '../ui/Card.jsx';
import StarRating from '../ui/StarRating.jsx';
import PersonName from '../people/PersonName.jsx';
import { noEmDash } from '../../lib/format.js';

// Analyst crystal-ball prediction for a recruit.
export default function CrystalBallCard({ pick }) {
  const c = pick;
  return (
    <Card className="tile" style={{ marginBottom: 10, padding: 14, display: 'flex', alignItems: 'center', gap: 14 }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 22, fontWeight: 850, color: 'var(--recruiting)' }}>{c.confidence ?? '-'}</div>
        <div style={{ fontSize: 10, color: 'var(--text-3)' }}>CONFIDENCE</div>
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 800 }}>
          <PersonName name={c.prospect} kind="recruit" /> <span style={{ color: 'var(--text-3)', fontWeight: 600 }}>{c.position}</span> <StarRating value={c.stars} />
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-2)', marginTop: 3 }}>
          <PersonName name={c.analyst} kind="analyst" /> predicts <b style={{ color: 'var(--recruiting)' }}>{c.prediction}</b>
        </div>
        {c.note && <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 3 }}>{noEmDash(c.note)}</div>}
      </div>
    </Card>
  );
}

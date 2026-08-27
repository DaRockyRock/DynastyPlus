import Card from '../ui/Card.jsx';
import { noEmDash } from '../../lib/format.js';

// Big letter grade plus summary for a recruiting / portal class.
export default function ClassGradeCard({ grade }) {
  const g = grade;
  return (
    <Card className="tile" style={{ marginBottom: 18, display: 'flex', alignItems: 'center', gap: 18 }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 40, fontWeight: 850, color: 'var(--portal)' }}>{g.grade || '-'}</div>
        <div style={{ fontSize: 10, color: 'var(--text-3)' }}>CLASS GRADE</div>
      </div>
      <div style={{ flex: 1, color: 'var(--text-2)', fontSize: 13, lineHeight: 1.55 }}>{noEmDash(g.summary || '')}</div>
    </Card>
  );
}

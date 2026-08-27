import Card from '../ui/Card.jsx';
import { noEmDash } from '../../lib/format.js';

// A player legacy page entry in the archive.
export default function LegacyCard({ player }) {
  const p = player;
  return (
    <Card className="tile" style={{ marginBottom: 10, padding: 14 }}>
      <div style={{ fontWeight: 800 }}>
        {p.player} <span style={{ color: 'var(--text-3)', fontWeight: 600, fontSize: 12 }}>{p.position || ''} - {p.years || ''}</span>
      </div>
      <div className="muted" style={{ marginTop: 5 }}>{noEmDash(p.summary || '')}</div>
      <div style={{ marginTop: 6, fontSize: 12, color: 'var(--heisman)', fontWeight: 700 }}>{noEmDash(p.legacy || '')}</div>
    </Card>
  );
}

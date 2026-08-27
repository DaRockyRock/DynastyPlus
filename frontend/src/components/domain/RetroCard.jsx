import Card from '../ui/Card.jsx';
import { noEmDash } from '../../lib/format.js';

// A season retrospective entry.
export default function RetroCard({ retro }) {
  return (
    <Card className="tile" style={{ marginBottom: 12 }}>
      <h3>{noEmDash(retro.headline)}</h3>
      <div className="muted" style={{ marginTop: 6 }}>{noEmDash(retro.body || '')}</div>
    </Card>
  );
}

import Card from '../ui/Card.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import { noEmDash } from '../../lib/format.js';

// Decade retrospective, shown every tenth season.
export default function DecadeCard({ decade }) {
  return (
    <Card style={{ padding: 18, marginTop: 16, border: '1px solid var(--heisman)' }}>
      <SectionTitle>Decade Retrospective - {decade.decade}</SectionTitle>
      <div className="muted">{noEmDash(decade.summary || '')}</div>
    </Card>
  );
}

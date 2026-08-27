import Card from '../ui/Card.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import { noEmDash } from '../../lib/format.js';

// National coaching-search narrative generated when a job opens.
export default function SearchBlock({ search }) {
  const s = search;
  return (
    <Card style={{ padding: 20, marginTop: 22, border: '1px solid var(--carousel)' }}>
      <SectionTitle>Active Search - {s.open_team}</SectionTitle>
      <p className="muted">{noEmDash(s.narrative || '')}</p>
      <div style={{ marginTop: 10 }}>
        Frontrunner: <b style={{ color: 'var(--carousel)' }}>{s.frontrunner || ''}</b>
      </div>
    </Card>
  );
}

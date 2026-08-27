import Card from '../ui/Card.jsx';
import PersonName from '../people/PersonName.jsx';
import { noEmDash } from '../../lib/format.js';

// An awards voter-panel member and their stated leaning.
export default function VoterCard({ voter }) {
  return (
    <Card className="tile">
      <h3 style={{ fontSize: 15 }}><PersonName name={voter.name} kind="voter" /></h3>
      <div style={{ fontSize: 12, color: 'var(--text-3)' }}>{voter.outlet || ''}</div>
      <div className="muted" style={{ marginTop: 8, fontStyle: 'italic' }}>&quot;{noEmDash(voter.lean || '')}&quot;</div>
    </Card>
  );
}

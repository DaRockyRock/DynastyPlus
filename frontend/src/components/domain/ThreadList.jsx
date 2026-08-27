import Card from '../ui/Card.jsx';
import { noEmDash } from '../../lib/format.js';

// Running list of persistent narrative threads from the narrative-memory layer.
export default function ThreadList({ threads = [] }) {
  return (
    <Card className="tile">
      {threads.length ? (
        threads.map((t, i) => (
          <div key={i} style={{ fontSize: 12.5, color: 'var(--text-2)', padding: '6px 0', borderBottom: '1px solid var(--border-soft)' }}>
            <b style={{ color: 'var(--text-3)' }}>W{t.week} - {t.category}:</b> {noEmDash(t.summary)}
          </div>
        ))
      ) : (
        <div className="muted">No threads recorded yet.</div>
      )}
    </Card>
  );
}

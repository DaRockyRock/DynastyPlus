import Card from '../ui/Card.jsx';
import TrendTag from '../ui/TrendTag.jsx';
import PersonName from '../people/PersonName.jsx';
import { noEmDash } from '../../lib/format.js';

// A single award's weekly watch list plus the voter-panel notes for it.
// `award` = { name, criteria, candidates: [...], notes: [...] }.
export default function AwardBlock({ award }) {
  const a = award;
  return (
    <Card className="award-block">
      <div className="a-head"><h3>{a.name}</h3></div>
      <div className="criteria">{a.criteria || ''}</div>
      {(a.candidates || []).map((c, i) => (
        <div className="cand-row" key={i}>
          <span className="cand-rank">{i + 1}</span>
          <div className="cand-info">
            <div className="c-name">
              <PersonName name={c.name} kind="player" /> <span style={{ color: 'var(--text-3)', fontWeight: 600, fontSize: 12 }}>{c.position || ''}</span>
            </div>
            <div className="c-meta">{c.team || ''} - {c.stat_line || ''}</div>
            {c.blurb && <div className="c-blurb">{noEmDash(c.blurb)}</div>}
          </div>
          <TrendTag trend={c.trend} />
        </div>
      ))}
      {(a.notes || []).length > 0 && (
        <div style={{ marginTop: 12, borderTop: '1px solid var(--border-soft)', paddingTop: 10 }}>
          {a.notes.map((n, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 5 }}>
              <b style={{ color: 'var(--text-2)' }}><PersonName name={n.voter} kind="voter" />:</b> {noEmDash(n.note)}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

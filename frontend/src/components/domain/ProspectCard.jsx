import Card from '../ui/Card.jsx';
import Avatar from '../ui/Avatar.jsx';
import StarRating from '../ui/StarRating.jsx';
import StageTag from '../ui/StageTag.jsx';
import MoneyValue from '../ui/MoneyValue.jsx';
import DealbreakerTag from '../ui/DealbreakerTag.jsx';
import PersonName from '../people/PersonName.jsx';
import { noEmDash, clamp } from '../../lib/format.js';

// Recruit card: rating, scouting report, recruitment status, analyst takes, and
// (when a live budget row is supplied) the prospect's NIL stage / offer / interest.
export default function ProspectCard({ prospect, committed = false, budget = null }) {
  const c = prospect;
  const ratingPct = c.rating ? (c.rating * 100).toFixed(2) : null;
  const b = budget || c;
  const hasBudget = b && (b.expected_nil != null || b.stage != null);
  const offerTone = b.offer ? (b.offer >= b.expected_nil ? 'pos' : 'neg') : 'default';
  return (
    <Card className="tile" style={{ marginBottom: 12, padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <Avatar label={c.position} size={40} />
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 800, fontSize: 15 }}><PersonName name={c.name} kind="recruit" /></div>
          <div style={{ fontSize: 12, color: 'var(--text-3)' }}>
            {c.hometown || ''}{c.from ? ` - from ${c.from}` : ''}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <StarRating value={c.stars} />
          {ratingPct && <div style={{ fontSize: 11, color: 'var(--text-3)' }}>{ratingPct}</div>}
        </div>
      </div>
      {c.scouting_report && <div className="muted" style={{ marginTop: 10 }}>{noEmDash(c.scouting_report)}</div>}
      {!committed && (c.leader || c.predicted) && (
        <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-2)' }}>
          Leader: <b>{c.leader || '-'}</b> - Predicted: <b style={{ color: 'var(--recruiting)' }}>{c.predicted || 'Undecided'}</b>
        </div>
      )}
      {c.visit && <div style={{ marginTop: 6, fontSize: 12, color: 'var(--cfp)' }}>{noEmDash(c.visit)}</div>}
      {hasBudget && (
        <div className="pc-budget">
          {b.stage && <StageTag stage={b.stage} />}
          {b.expected_nil != null && <span className="pc-b-item">Exp <MoneyValue value={b.expected_nil} /></span>}
          <span className="pc-b-item">Offer <MoneyValue value={b.offer || 0} tone={offerTone} /></span>
          {b.interest != null && (
            <span className="pc-b-item pc-int">Int
              <span className="nt-bar-mini"><i style={{ width: `${clamp(b.interest)}%` }} /></span>
              <b>{b.interest}</b>
            </span>
          )}
          {b.dealbreaker && <DealbreakerTag value={b.dealbreaker} />}
        </div>
      )}
      {(Array.isArray(c.analyst_takes) ? c.analyst_takes : []).map((a, i) => (
        <div key={i} style={{ marginTop: 8, fontSize: 12, color: 'var(--text-3)', borderLeft: '2px solid var(--border)', paddingLeft: 10 }}>
          <b style={{ color: 'var(--text-2)' }}><PersonName name={a.analyst} kind="analyst" />:</b> {noEmDash(a.take)}
        </div>
      ))}
    </Card>
  );
}

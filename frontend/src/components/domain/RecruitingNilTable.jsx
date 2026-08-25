import Card from '../ui/Card.jsx';
import Button from '../ui/Button.jsx';
import MoneyValue from '../ui/MoneyValue.jsx';
import StageTag from '../ui/StageTag.jsx';
import StarRating from '../ui/StarRating.jsx';
import DealbreakerTag from '../ui/DealbreakerTag.jsx';
import { clamp } from '../../lib/format.js';

// The recruiting-NIL spreadsheet: every prospect with their stage, expected
// amount, current offer, and momentum. `onOffer(row)` opens the offer editor.
export default function RecruitingNilTable({ rows = [], onOffer, title = 'Recruiting NIL' }) {
  return (
    <Card className="nil-table">
      <div className="nt-bar"><h3>{title}</h3><span className="nt-count">{rows.length} prospects</span></div>
      <div className="nt-head nt-grid">
        <span>Prospect</span><span>Stage</span><span>Expected</span><span>Offer</span><span>Interest</span><span />
      </div>
      {rows.map((r) => {
        const tone = r.offer ? (r.offer >= r.expected_nil ? 'pos' : 'neg') : 'default';
        return (
          <div className="nt-row nt-grid" key={r.id}>
            <div className="nt-name">
              <b>{r.name}</b>
              <span className="nt-sub">
                {r.position} <StarRating value={r.stars} />{r.committed ? ' - Commit' : ''}
              </span>
              <DealbreakerTag value={r.dealbreaker} />
            </div>
            <StageTag stage={r.stage} />
            <MoneyValue value={r.expected_nil} />
            <MoneyValue value={r.offer} tone={tone} />
            <span className="nt-interest">
              <span className="nt-bar-mini"><i style={{ width: `${clamp(r.interest)}%` }} /></span>
              <span className="nt-int-num">{r.interest}</span>
            </span>
            {onOffer && <Button onClick={() => onOffer(r)}>{r.offer > 0 ? 'Edit Offer' : 'Offer'}</Button>}
          </div>
        );
      })}
    </Card>
  );
}

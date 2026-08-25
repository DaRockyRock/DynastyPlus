import Card from '../ui/Card.jsx';
import MoneyValue from '../ui/MoneyValue.jsx';
import PointsValue from '../ui/PointsValue.jsx';
import BudgetMeter from '../ui/BudgetMeter.jsx';
import AllocationBar from '../ui/AllocationBar.jsx';
import { formatMoney, formatPoints } from '../../lib/format.js';

// Top-of-hub readout: Dynasty Points + the two NIL pools + weekly recruiting
// hours, each with a meter. `compact` drops the allocation bar (used as a
// header strip on the Recruiting page).
export default function BudgetSummaryBar({ snapshot, compact = false }) {
  if (!snapshot) return null;
  const dp = snapshot.dynasty_points;
  const rec = snapshot.nil.recruiting;
  const ros = snapshot.nil.roster;
  const hrs = snapshot.recruiting_hours;

  return (
    <Card className="budget-summary">
      <div className="bs-grid">
        <div className="bs-cell">
          <div className="bs-label">Dynasty Points</div>
          <div className="bs-value">
            <PointsValue value={dp.available} tone={dp.available < 0 ? 'neg' : 'pos'} />
            <small> of {formatPoints(dp.total)}</small>
          </div>
          <BudgetMeter value={dp.total - dp.available} max={dp.total} tone="heisman" />
        </div>
        <div className="bs-cell">
          <div className="bs-label">Recruiting NIL</div>
          <div className="bs-value">
            <MoneyValue value={rec.available} tone={rec.available < 0 ? 'neg' : 'nil'} />
            <small> of {formatMoney(rec.pool)}</small>
          </div>
          <BudgetMeter value={rec.committed} max={rec.pool} tone="nil" />
        </div>
        <div className="bs-cell">
          <div className="bs-label">Roster NIL</div>
          <div className="bs-value">
            <MoneyValue value={ros.available} tone={ros.available < 0 ? 'neg' : 'pos'} />
            <small> of {formatMoney(ros.pool)}</small>
          </div>
          <BudgetMeter value={ros.committed} max={ros.pool} tone="recruiting" />
        </div>
        <div className="bs-cell">
          <div className="bs-label">Recruiting Hours</div>
          <div className="bs-value">
            <span className="bs-num">{hrs.remaining}</span>
            <small> of {hrs.total} this week</small>
          </div>
          <BudgetMeter value={hrs.spent} max={hrs.total} tone="cfp" />
        </div>
      </div>
      {!compact && (
        <div className="bs-alloc">
          <AllocationBar total={dp.total} allocations={dp.allocations} />
        </div>
      )}
    </Card>
  );
}

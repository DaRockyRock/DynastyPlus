import { formatMoney } from '../../lib/format.js';

// Compact summary shown above the contact list on the phone's Recruits tab:
// how much recruiting NIL is left and how many weekly hours remain.
export default function RecruitBudgetStrip({ snapshot }) {
  if (!snapshot) return null;
  const rec = snapshot.nil?.recruiting;
  const hrs = snapshot.recruiting_hours;
  if (!rec || !hrs) return null;

  return (
    <div className="recruit-budget-strip">
      <div className="rbs-item">
        <span className="rbs-k">Recruiting NIL</span>
        <span className="rbs-v">{formatMoney(rec.available)}</span>
      </div>
      <div className="rbs-sep" />
      <div className="rbs-item">
        <span className="rbs-k">Hours Left</span>
        <span className="rbs-v">{hrs.remaining}/{hrs.total}</span>
      </div>
    </div>
  );
}

import { clamp } from '../../lib/format.js';

// Segmented broadcast gauge for "used of available" budget readouts (DP pool,
// NIL pool, recruiting hours). `tone` picks the fill color from the token set.
export default function BudgetMeter({ value = 0, max = 100, label, caption, tone = 'nil' }) {
  const pct = max > 0 ? clamp((value / max) * 100) : 0;
  const over = value > max;
  return (
    <div className="budget-meter">
      {label && <div className="bm-label">{label}</div>}
      <div className="bm-track" style={{ '--bm': over ? 'var(--loss)' : `var(--${tone})` }}>
        <span style={{ width: `${Math.max(2, pct)}%` }} />
      </div>
      {caption && <div className="bm-caption">{caption}</div>}
    </div>
  );
}

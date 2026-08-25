import { formatPoints } from '../../lib/format.js';

// Dynasty Points split across the three blueprint categories, plus the open
// (unallocated) remainder. A single proportional bar with an optional legend.
const SEGS = [
  { key: 'coaching_staff', label: 'Staff', color: 'var(--carousel)' },
  { key: 'facilities', label: 'Facilities', color: 'var(--cfp)' },
  { key: 'nil', label: 'NIL', color: 'var(--nil)' },
];

export default function AllocationBar({ allocations = {}, total = 0, showLegend = true }) {
  const segs = SEGS.map((s) => ({ ...s, value: Math.max(0, allocations[s.key] || 0) }));
  const used = segs.reduce((sum, s) => sum + s.value, 0);
  const free = Math.max(0, total - used);
  return (
    <div className="alloc">
      <div className="alloc-bar">
        {segs.map((s) => s.value > 0 && (
          <span key={s.key} className="alloc-seg" style={{ flexGrow: s.value, background: s.color }} title={s.label} />
        ))}
        {free > 0 && <span className="alloc-seg free" style={{ flexGrow: free }} title="Open" />}
      </div>
      {showLegend && (
        <div className="alloc-legend">
          {segs.map((s) => (
            <span key={s.key} className="alloc-leg"><i style={{ background: s.color }} />{s.label} <b>{formatPoints(s.value)}</b></span>
          ))}
          <span className="alloc-leg"><i className="free" />Open <b>{formatPoints(free)}</b></span>
        </div>
      )}
    </div>
  );
}

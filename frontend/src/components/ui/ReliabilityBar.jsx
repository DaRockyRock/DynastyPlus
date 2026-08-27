import { clamp } from '../../lib/format.js';

// Compact 0-100 reliability/credibility meter used on reporters and rumors.
export default function ReliabilityBar({ score, showValue = true }) {
  const pct = clamp(score);
  const color = pct >= 85 ? '#22c55e' : pct >= 70 ? '#eab308' : '#ef4444';
  return (
    <span className="reliability">
      <span className="rel-bar"><span style={{ width: `${pct}%`, background: color }} /></span>
      {showValue && pct}
    </span>
  );
}

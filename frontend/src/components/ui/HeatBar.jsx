import { clamp } from '../../lib/format.js';

// Coaching hot-seat heat index (0-100), green to red gradient.
export default function HeatBar({ value }) {
  const pct = clamp(value);
  return (
    <div className="heat-meter">
      <div className="heat-bar"><span style={{ width: `${Math.max(4, pct)}%` }} /></div>
      <div className="heat-val">{value} / 100</div>
    </div>
  );
}

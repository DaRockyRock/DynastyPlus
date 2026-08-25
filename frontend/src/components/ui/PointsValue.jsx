import { formatPoints } from '../../lib/format.js';

// A Dynasty Points figure with a trailing unit. The program budget currency.
export default function PointsValue({ value, unit = 'DP', tone = 'default', className = '' }) {
  return (
    <span className={['points', tone, className].filter(Boolean).join(' ')}>
      {formatPoints(value)}
      <small>{unit}</small>
    </span>
  );
}

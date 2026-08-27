import { clamp } from '../../lib/format.js';

// Linear progress bar (team-colored fill). Used by the generation loading overlay.
export default function ProgressBar({ value = 0 }) {
  return (
    <div className="loading-bar">
      <div className="loading-bar-fill" style={{ width: `${clamp(value)}%` }} />
    </div>
  );
}

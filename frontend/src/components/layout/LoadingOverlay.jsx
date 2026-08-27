import TeamLogo from '../ui/TeamLogo.jsx';
import ProgressBar from '../ui/ProgressBar.jsx';
import { hexColor } from '../../lib/format.js';

export default function LoadingOverlay({ active, week, team, progress = 0, total = 0, module, subStep, title, caption }) {
  if (!active) return null;
  const pct = total ? Math.max(8, Math.round((progress / total) * 100)) : 8;
  // `title`/`caption` let a non-advance pass (e.g. the post-game press conference)
  // say what it is doing instead of the default week-advance copy.
  const heading = title || `Advancing to Week ${week}`;
  const sub = caption || "Generating this week's media";
  // No module yet: show "Initializing" only for the default (week-advance) pass;
  // a titled pass leaves the slot empty so the live dot reads as a working pulse.
  const moduleLabel = module ? module.replace(/_/g, ' ') : (title ? null : 'Initializing');
  return (
    <div className="loading">
      <div className="loading-card">
        <div className="loading-logo-panel">
          <TeamLogo espnId={team?.espn_id} abbr={team?.abbreviation} name={team?.name} color={hexColor(team?.color)} size={84} plate={false} />
        </div>
        <div className="loading-body">
          <p className="loading-eyebrow">Dynasty Media</p>
          <h3 className="loading-title">{heading}</h3>
          <p className="loading-sub">{sub}</p>
          <ProgressBar value={pct} />
          <div className="loading-status">
            <span className="loading-live-dot" />
            {moduleLabel && <span className="loading-status-module">{moduleLabel}</span>}
            {subStep && <span className="loading-status-sep">/</span>}
            {subStep && <span className="loading-substep">{subStep}</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

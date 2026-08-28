import { RefreshIcon } from '../ui/icons.jsx';

// Top-bar readout while Tools watches the selected dynasty save. Two states:
//   active  - watcher connected, pulsing dot, "Live / Watching save"
//   waiting - no save detected yet, steady amber dot, "Waiting / No save"
// An optional Sync button forces an immediate refresh of the current week.
export default function LiveStatus({ active = false, detail, onSync }) {
  const state = active ? 'Live' : 'Waiting';
  const sub = detail || (active ? 'Watching save' : 'No save detected');
  return (
    <div className={`live-status ${active ? 'is-live' : 'is-waiting'}`} role="status" aria-live="polite">
      <span className="live-status-dot" aria-hidden="true" />
      <span className="live-status-text">
        <span className="live-status-state">{state}</span>
        <span className="live-status-detail">{sub}</span>
      </span>
      {onSync && (
        <button
          type="button"
          className="live-status-sync"
          onClick={onSync}
          title="Refresh now"
          aria-label="Refresh now"
        >
          <RefreshIcon size={15} />
        </button>
      )}
    </div>
  );
}

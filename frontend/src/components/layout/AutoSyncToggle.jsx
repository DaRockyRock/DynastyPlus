import ToggleSwitch from '../ui/ToggleSwitch.jsx';

// The global auto-sync master switch, shown at the top-right of the header in
// When on, a new game save automatically re-asserts the user's
// polls and pushes decided custom-playoff matchups back into the save. When
// off, nothing writes on its own, so the user can edit rankings/brackets
// without the watcher re-asserting under them; they sync/apply by hand.
export default function AutoSyncToggle({ enabled = true, onChange, busy = false }) {
  return (
    <div
      className={`autosync-toggle${busy ? ' busy' : ''}`}
      title={enabled
        ? 'Auto-sync is on: new game saves update your polls and playoff bracket automatically.'
        : 'Auto-sync is off: nothing writes automatically. Use Sync to push changes yourself.'}
    >
      <ToggleSwitch
        checked={enabled}
        onChange={(v) => !busy && onChange?.(v)}
        label="Auto-sync"
      />
    </div>
  );
}

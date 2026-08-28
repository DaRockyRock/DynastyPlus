import Button from '../ui/Button.jsx';

// Action banner for the live playoff view. Deliberately quiet: it renders
// NOTHING in normal play and appears only when the user must act:
//
// 1. needs_write - the app has new matchups (or a rewind) ready but has NOT
//    touched the save. The user closes the dynasty in CFB 27 (main menu) and
//    presses the update button, which POSTs /api/playoff/apply.
// 2. awaiting_reload - the save has been updated and the game has not run
//    the new matchups yet: load the dynasty and play. Clears by itself once
//    results from the written games appear.
// 3. problems - the format itself cannot build.

export default function PlayoffLiveStatus({
  needsWrite = false,
  awaitingReload = false,
  applying = false,
  onApply,
  problems = [],
}) {
  if (!needsWrite && !awaitingReload && !(problems || []).length) return null;
  return (
    <div className="plv-status">
      {needsWrite ? (
        <div className="plv-banner plv-live">
          <span className="plv-dot" />
          <div className="plv-banner-text">
            <span className="plv-state">Action needed</span>
            <span className="plv-title">New playoff games are ready</span>
            <span className="plv-desc">
              In CFB 27, exit the dynasty to the game's main menu, then press
              Update dynasty file. The app writes the next set of matchups
              into the save so the game picks them up when you load it.
            </span>
            <div className="plv-actions">
              <Button variant="accent" onClick={onApply} spinning={applying} disabled={applying}>
                {applying ? 'Updating' : 'Update dynasty file'}
              </Button>
            </div>
          </div>
        </div>
      ) : awaitingReload && (
        <div className="plv-banner plv-gold">
          <span className="plv-dot" />
          <div className="plv-banner-text">
            <span className="plv-state">Save updated</span>
            <span className="plv-title">You're good to go</span>
            <span className="plv-desc">
              The dynasty file carries this wave's matchups. Load the dynasty
              in CFB 27 and play or sim the playoff games on the schedule.
            </span>
          </div>
        </div>
      )}
      {(problems || []).map((p, i) => (
        <p key={i} className="plv-line plv-line-warn">{p}</p>
      ))}
    </div>
  );
}

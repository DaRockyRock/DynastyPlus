import Button from '../ui/Button.jsx';
import ProgressBar from '../ui/ProgressBar.jsx';
import { CheckIcon, RefreshIcon } from '../ui/icons.jsx';

export default function WeekSyncModal({ status, onContinue }) {
  const phase = status?.phase;
  if (!status || phase === 'idle' || phase === 'complete') return null;
  const needsReload = !!status.reload_required;
  const failed = phase === 'error';
  const updatingTools = phase === 'tools';
  const progress = Number.isFinite(status.progress) ? status.progress
    : phase === 'detected' ? 8
      : phase === 'recruiting' ? 42
        : updatingTools ? 78
          : needsReload ? 100 : 0;
  const recruitingDone = updatingTools || needsReload || phase === 'complete';
  const toolsDone = needsReload || phase === 'complete';
  return (
    <div className="week-sync" role="alertdialog" aria-modal="true" aria-label="Dynasty file update">
      <div className="week-sync-card">
        <p className="week-sync-eyebrow">Week Sync</p>
        <h3>{needsReload ? 'Dynasty file updated' : failed ? 'Recruiting update stopped' : 'Preparing the new week'}</h3>
        <div className="week-sync-progress" aria-live="polite">
          <div><span>{Math.round(progress)}%</span><small>{status.message || 'Preparing dynasty tools'}</small></div>
          <ProgressBar value={progress} />
        </div>
        <div className={`week-sync-step ${phase === 'detected' ? 'active' : 'done'}`}>
          <span>{phase === 'detected' ? <RefreshIcon /> : <CheckIcon />}</span>
          <div><strong>CFB 27 save detected</strong><small>{status.save || 'Current dynasty save'}</small></div>
        </div>
        <div className={`week-sync-step ${phase === 'recruiting' ? 'active' : recruitingDone ? 'done' : failed ? 'error' : 'pending'}`}>
          <span>{phase === 'recruiting' ? <RefreshIcon /> : recruitingDone ? <CheckIcon /> : null}</span>
          <div>
            <strong>Check offers and team attention</strong>
            <small>{phase === 'recruiting' ? status.message : recruitingDone ? 'Recruiting check complete' : 'Waiting to start'}</small>
          </div>
        </div>
        <div className={`week-sync-step ${updatingTools ? 'active' : toolsDone ? 'done' : failed ? 'error' : 'pending'}`}>
          <span>{updatingTools ? <RefreshIcon /> : toolsDone ? <CheckIcon /> : null}</span>
          <div>
            <strong>Finish weekly dynasty tools</strong>
            <small>{updatingTools ? status.message : needsReload ? 'Continuing in the background' : toolsDone ? 'Weekly tools ready' : 'Runs after the recruiting check'}</small>
          </div>
        </div>
        {needsReload && (
          <div className="week-sync-reload">
            <strong>Reload this dynasty in CFB 27</strong>
            <p>
              Return to the CFB 27 main menu and load this dynasty again. You do not need to
              close the game or Dynasty+. Continue here only after the reload finishes.
            </p>
          </div>
        )}
        {failed && <p className="week-sync-error">{status.message}</p>}
        {(needsReload || failed) && (
          <Button variant="accent" onClick={onContinue}>
            {needsReload ? 'I reloaded the dynasty' : 'Continue without correction'}
          </Button>
        )}
      </div>
    </div>
  );
}

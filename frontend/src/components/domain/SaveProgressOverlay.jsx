import { AlertIcon, CheckIcon, RefreshIcon } from '../ui/icons.jsx';

// Blocking overlay shown while the Conference Setup save runs. Saving can take
// a moment (it decodes and rewrites the dynasty save, and the first logo-mod
// build mirrors the game files), so this shows the phases as a checklist: each
// step is pending (hollow dot), active (spinner), done (check), or skipped
// (alert) when an optional step (like the logo mod) could not run but the save
// itself still succeeded.
// Presentational: `steps` is [{ label, note?, status }]; `open` toggles it.
export default function SaveProgressOverlay({ open, steps = [], title = 'Saving to your dynasty' }) {
  if (!open) return null;
  return (
    <div className="cs-save-overlay" role="alertdialog" aria-modal="true" aria-label={title}>
      <div className="cs-save-card">
        <div className="cs-save-title">{title}</div>
        <ul className="cs-save-steps">
          {steps.map((s, i) => (
            <li key={i} className={`cs-save-step ${s.status}`}>
              <span className="cs-save-mark" aria-hidden="true">
                {s.status === 'done' ? <CheckIcon />
                  : s.status === 'active' ? <RefreshIcon />
                  : s.status === 'skipped' ? <AlertIcon />
                  : <span className="cs-save-dot" />}
              </span>
              <span className="cs-save-step-text">
                <span className="cs-save-step-label">{s.label}</span>
                {s.note && <span className="cs-save-step-note">{s.note}</span>}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

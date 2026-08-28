// The playoff walkthrough: one box per phase (reach the playoff, each round,
// completion) rendered above the live bracket, driven by the backend's
// `guide` payload (playoff_live._build_guide). The current phase expands to
// its full step list with the user's current step highlighted; finished and
// upcoming phases collapse to a title + progress chip so the whole journey
// reads at a glance. The page's polling (plus the saves watcher behind it)
// keeps the cursor tracking the dynasty save in near real time.

const STATE_LABEL = { done: 'Done', current: 'You are here', upcoming: 'Up next' };

function Step({ step }) {
  return (
    <li className={`pgd-step pgd-step-${step.state}`}>
      <span className="pgd-step-mark" aria-hidden="true">
        {step.state === 'done' ? '✓' : ''}
      </span>
      <span className="pgd-step-body">
        <span className="pgd-step-label">{step.label}</span>
        {step.state === 'current' && step.detail && (
          <span className="pgd-step-detail">{step.detail}</span>
        )}
      </span>
    </li>
  );
}

export default function PlayoffGuide({ guide }) {
  const phases = guide?.phases || [];
  if (!phases.length) return null;
  return (
    <div className="pgd">
      {phases.map((ph) => (
        <section key={ph.key} className={`pgd-phase pgd-phase-${ph.state}`}>
          <header className="pgd-head">
            <span className="pgd-title">{ph.title}</span>
            <span className={`pgd-chip pgd-chip-${ph.state}`}>{STATE_LABEL[ph.state] || ph.state}</span>
          </header>
          {(ph.progress || ph.user_line) && (
            <div className="pgd-meta">
              {ph.progress && <span className="pgd-progress">{ph.progress}</span>}
              {ph.user_line && <span className="pgd-user">{ph.user_line}</span>}
            </div>
          )}
          {ph.state === 'current' && (
            <ol className="pgd-steps">
              {(ph.steps || []).map((s) => <Step key={s.id} step={s} />)}
            </ol>
          )}
        </section>
      ))}
    </div>
  );
}

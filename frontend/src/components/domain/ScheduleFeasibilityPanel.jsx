import PanelCard from '../ui/PanelCard.jsx';

// The schedule math report: whether a season satisfying every rule exists,
// and if not, exactly which rule breaks and how to fix it. Renders the
// feasibility payload from /api/schedule/setup (or a generate failure).
export default function ScheduleFeasibilityPanel({ feasibility }) {
  const errors = feasibility?.errors || [];
  const warnings = feasibility?.warnings || [];
  const ok = feasibility ? feasibility.ok && errors.length === 0 : true;
  return (
    <PanelCard
      title="Schedule Math"
      right={ok ? 'Possible' : `${errors.length} problem${errors.length === 1 ? '' : 's'}`}
    >
      {ok && (
        <div className="sr-feas-ok">
          <span className="dot" />
          Every rule checks out. A schedule satisfying all of them exists.
        </div>
      )}
      <div className="sr-feas-list">
        {errors.map((e, i) => (
          <div className="sr-feas-item" key={`e${i}`}>
            <div className="sr-feas-msg">{e.message}</div>
            {e.fix && <div className="sr-feas-fix">{e.fix}</div>}
          </div>
        ))}
        {warnings.map((w, i) => (
          <div className="sr-feas-item warn" key={`w${i}`}>
            <div className="sr-feas-msg">{w.message}</div>
            {w.fix && <div className="sr-feas-fix">{w.fix}</div>}
          </div>
        ))}
      </div>
    </PanelCard>
  );
}

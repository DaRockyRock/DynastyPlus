// Small top-bar indicator that the app is viewing a simulated (Debug) season
// rather than a live save. Pulsing dot + SIM + week.
export default function SimStatusBadge({ week, onClick }) {
  return (
    <button type="button" className="sim-badge" onClick={onClick} title="Simulated season (Debug mode)">
      <span className="sim-badge-dot" />
      SIM<span className="sim-badge-wk">Wk {week}</span>
    </button>
  );
}

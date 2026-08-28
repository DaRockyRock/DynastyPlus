// The game's top-right HUD readout chip: colored icon, tiny uppercase label,
// bright value, optional mini meter (job-security style). `accent` sets the
// icon/meter color; `bar` (0-100) renders the meter.
export default function HudChip({ icon = null, label, value, accent, bar = null, title }) {
  const style = accent ? { '--hc-accent': accent } : undefined;
  return (
    <span className="hud-chip" style={style} title={title || label}>
      {icon && <span className="hc-ico">{icon}</span>}
      {label && <span className="hc-label">{label}</span>}
      {value != null && <span className="hc-value">{value}</span>}
      {bar != null && (
        <span className="hc-bar">
          <i style={{ width: `${Math.max(0, Math.min(100, bar))}%` }} />
        </span>
      )}
    </span>
  );
}

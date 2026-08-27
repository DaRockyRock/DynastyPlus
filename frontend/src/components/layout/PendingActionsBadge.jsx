// A small indicator for coach actions queued in the companion inbox, waiting for
// the Simulator to drain them. Shown in the Dynasty+ top bar. Renders nothing
// when there is nothing pending.
export default function PendingActionsBadge({ count = 0, onClick }) {
  if (!count) return null;
  const label = `${count} queued`;
  return (
    <button
      type="button"
      className="pending-badge"
      onClick={onClick}
      title={`${count} coach action${count > 1 ? 's' : ''} queued for the Simulator`}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '4px 10px', borderRadius: 999, cursor: onClick ? 'pointer' : 'default',
        background: 'color-mix(in srgb, var(--team) 22%, transparent)',
        border: '1px solid color-mix(in srgb, var(--team) 55%, transparent)',
        color: 'var(--text-1, #e9eef5)', font: '700 11px/1 "Saira Condensed", sans-serif',
        letterSpacing: '0.06em', textTransform: 'uppercase', whiteSpace: 'nowrap',
      }}
    >
      <span aria-hidden style={{
        width: 6, height: 6, borderRadius: 999,
        background: 'var(--team-alt, #f5f5f5)', boxShadow: '0 0 6px var(--team)',
      }} />
      {label}
    </button>
  );
}

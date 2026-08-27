// A small red notification bubble showing an unread count, for an action button
// or icon. Renders nothing when count is zero or less. Caps the label at 99+.
export default function CountBadge({ count = 0, max = 99 }) {
  if (!count || count <= 0) return null;
  const label = count > max ? `${max}+` : String(count);
  return (
    <span className="count-badge" aria-label={`${count} unread`}>{label}</span>
  );
}

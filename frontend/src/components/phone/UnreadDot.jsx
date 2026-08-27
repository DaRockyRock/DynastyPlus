// The blue iMessage-style unread marker for a Messages list row. Renders nothing
// unless there is an unread inbound text, so a row can always include it.
export default function UnreadDot({ unread = false, size = 9 }) {
  if (!unread) return null;
  return <span className="unread-dot" style={{ width: size, height: size }} aria-label="Unread" />;
}

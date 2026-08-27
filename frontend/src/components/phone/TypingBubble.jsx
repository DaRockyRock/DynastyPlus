// Animated "typing" indicator. `variant="bubble"` (default) is the in-conversation
// chat bubble; `variant="inline"` is a compact, background-less version for a
// Messages list row, shown while a contact is composing a reply you have not
// opened yet.
export default function TypingBubble({ variant = 'bubble' }) {
  return (
    <div className={`typing-bubble${variant === 'inline' ? ' inline' : ''}`} aria-label="typing">
      <i /><i /><i />
    </div>
  );
}

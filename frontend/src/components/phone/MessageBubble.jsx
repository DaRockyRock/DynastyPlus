import { noEmDash } from '../../lib/format.js';

// An iMessage-style chat bubble. `from` is 'me' (the coach, blue) or 'them'
// (the contact, gray). `tail` draws the curved tail on the last bubble of a run.
export default function MessageBubble({ from = 'them', text, tail = true }) {
  const cls = ['bubble', from === 'me' ? 'me' : 'them', tail ? 'tail' : ''].filter(Boolean).join(' ');
  return <div className={cls}>{noEmDash(text)}</div>;
}

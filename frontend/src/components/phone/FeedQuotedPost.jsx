import VerifiedBadge from '../ui/VerifiedBadge.jsx';
import { noEmDash } from '../../lib/format.js';

// A nested, non-interactive snapshot of the post a quote-post is quoting. Shown
// inside the quoting post's body, like a quote-tweet card.
export default function FeedQuotedPost({ quoted }) {
  if (!quoted) return null;
  const q = quoted;
  return (
    <div className="feed-quoted">
      <div className="fq-head">
        {q.image
          ? <img className="fq-avatar" src={q.image} alt="" />
          : <span className="fq-avatar mono">{q.avatar || (q.author_name || '?').slice(0, 2)}</span>}
        <span className="fq-name">{q.author_name}</span>
        <VerifiedBadge verified={q.verified} size={12} />
        <span className="fq-handle">@{q.handle}</span>
      </div>
      <div className="fq-text">{noEmDash(q.text || '')}</div>
    </div>
  );
}

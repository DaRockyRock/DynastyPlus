import VerifiedBadge from '../ui/VerifiedBadge.jsx';

// The identity line of a feed post: display name, verified check, @handle and the
// relative timestamp. When the author is textable (a media member or personality)
// the name acts as a button that opens a DM via the existing texting engine; for
// brands and fans it is plain text.
export default function FeedAuthor({ post, onText }) {
  const p = post;
  const textable = p.textable && onText;
  const open = (e) => {
    e.stopPropagation();
    if (textable) onText({ name: p.author_name, kind: p.text_kind || 'media' });
  };
  return (
    <div className="feed-author">
      <button
        type="button"
        className={`fa-name${textable ? ' textable' : ''}`}
        onClick={open}
        disabled={!textable}
        title={textable ? `Text ${p.author_name}` : undefined}
      >
        {p.author_name}
      </button>
      <VerifiedBadge verified={p.verified} />
      <span className="fa-handle">@{p.handle}</span>
      <span className="fa-dot">·</span>
      <span className="fa-time">{p.timestamp}</span>
    </div>
  );
}

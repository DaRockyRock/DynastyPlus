import { MessageIcon, RepostIcon, HeartIcon } from '../ui/icons.jsx';
import { compactCount } from '../../lib/format.js';

// The action row under a feed post: reply / repost / like counts. Like is the
// only interactive control (the coach reads + likes; he does not reply or post).
// A like bumps the displayed count by one and fills the heart.
export default function FeedEngagementRow({ metrics = {}, liked = false, onLike }) {
  const likes = (metrics.likes || 0) + (liked ? 1 : 0);
  const toggle = (e) => {
    e.stopPropagation();
    if (onLike) onLike();
  };
  return (
    <div className="feed-engagement">
      <span className="fe-stat" aria-label="replies">
        <MessageIcon size={15} />{compactCount(metrics.replies)}
      </span>
      <span className="fe-stat" aria-label="reposts">
        <RepostIcon size={15} />{compactCount(metrics.reposts)}
      </span>
      <button
        type="button"
        className={`fe-stat like${liked ? ' active' : ''}`}
        onClick={toggle}
        aria-pressed={liked}
        aria-label={liked ? 'Unlike' : 'Like'}
      >
        <HeartIcon size={15} filled={liked} />{compactCount(likes)}
      </button>
    </div>
  );
}

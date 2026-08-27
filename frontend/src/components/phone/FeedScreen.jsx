import { useContext, useEffect, useMemo } from 'react';
import { AppContext } from '../../context/AppContext.jsx';
import FeedPostCard from './FeedPostCard.jsx';
import EmptyState from '../ui/EmptyState.jsx';

// The social-feed timeline inside the phone. Reads the week's generated posts and
// the coach's like state from AppContext (with prop overrides so Storybook can
// render it with fixtures). Replies are threaded under the post they answer.
// Opening the Feed marks the week seen, which clears the unseen badge.
export default function FeedScreen({
  posts: postsProp, likes: likesProp, onLike, onText, onOpenArticle, onDone, onSeen, week,
}) {
  const ctx = useContext(AppContext);
  const posts = postsProp || ctx?.feedPosts || [];
  const likes = likesProp || ctx?.feedLikes || {};
  const like = onLike || ctx?.toggleFeedLike;
  const text = onText || ctx?.textPerson;
  const openArticle = onOpenArticle || ctx?.openArticle;
  const done = onDone || ctx?.closePhone;
  const markSeen = onSeen || ctx?.markFeedSeen;
  const wk = week ?? ctx?.pointer?.week;

  // Opening the Feed clears its unseen badge for the current week.
  useEffect(() => {
    if (markSeen && wk != null) markSeen(wk);
  }, [markSeen, wk]);

  // Thread replies under their parent; quote-posts stay standalone in the timeline.
  const order = useMemo(() => {
    const byId = Object.fromEntries(posts.map((p) => [p.id, p]));
    const repliesByParent = {};
    for (const p of posts) {
      if (p.reply_to && byId[p.reply_to]) {
        (repliesByParent[p.reply_to] ||= []).push(p);
      }
    }
    // Strict post-time order, newest first, by the synthetic `ts` (newer =
    // larger). No post type is pinned: a breaking scoop leads only when it is the
    // most recent event, and sits in its true chronological spot otherwise. This
    // is what keeps a reaction that the backend merged in after the initial roll
    // from landing mid-list. Posts without a ts keep their incoming order via a
    // stable fallback.
    const tsOf = (p) => (typeof p.ts === 'number' ? p.ts : -Infinity);
    const roots = posts
      .filter((p) => !(p.reply_to && byId[p.reply_to]))
      .sort((a, b) => tsOf(b) - tsOf(a));
    const out = [];
    for (const root of roots) {
      out.push({ post: root });
      for (const rep of repliesByParent[root.id] || []) {
        out.push({ post: rep, reply: true, replyingTo: root.handle });
      }
    }
    return out;
  }, [posts]);

  return (
    <div className="msg-screen feed-screen">
      <div className="msg-titlebar">
        <span className="msg-title">Feed</span>
        {done && <button className="msg-edit" onClick={done}>Done</button>}
      </div>
      <div className="feed-list">
        {order.length === 0 ? (
          <EmptyState>No posts yet this week. Check back after the next slate.</EmptyState>
        ) : (
          order.map(({ post, reply, replyingTo }) => (
            <FeedPostCard
              key={post.id}
              post={post}
              reply={reply}
              replyingTo={replyingTo}
              liked={!!likes[post.id]}
              onLike={like ? () => like(post.id) : undefined}
              onText={text}
              onOpenArticle={openArticle}
            />
          ))
        )}
      </div>
    </div>
  );
}

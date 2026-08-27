import TeamLogo from '../ui/TeamLogo.jsx';
import FeedAuthor from './FeedAuthor.jsx';
import FeedRefCard from './FeedRefCard.jsx';
import FeedQuotedPost from './FeedQuotedPost.jsx';
import FeedEngagementRow from './FeedEngagementRow.jsx';
import FeedBreakingTag from './FeedBreakingTag.jsx';
import { noEmDash } from '../../lib/format.js';

// One post in the feed timeline. Composes the author line, body text, an optional
// quoted post and reference card, and the engagement row. `reply` indents it under
// its parent. All interaction is passed in: onLike (toggle), onText (open a DM with
// the author), onOpenArticle (open the article reader for an article reference).
export default function FeedPostCard({ post, liked = false, reply = false, replyingTo, onLike, onText, onOpenArticle }) {
  const p = post;
  return (
    <article className={`feed-post${reply ? ' reply' : ''}${p.breaking ? ' breaking' : ''}`}>
      <div className="fp-avatar">
        {p.image
          ? <img src={p.image} alt="" />
          : p.team_espn_id != null
            ? <TeamLogo espnId={p.team_espn_id} name={p.author_name} size={44} plate={false} />
            : <span className="fp-mono">{p.avatar || (p.author_name || '?').slice(0, 2)}</span>}
      </div>
      <div className="fp-body">
        <FeedAuthor post={p} onText={onText} />
        {replyingTo && <div className="fp-replying">Replying to @{replyingTo}</div>}
        {p.breaking && <FeedBreakingTag />}
        <div className="fp-text">{noEmDash(p.text || '')}</div>
        {p.quoted && <FeedQuotedPost quoted={p.quoted} />}
        {p.ref && <FeedRefCard refData={p.ref} onOpenArticle={onOpenArticle} />}
        <FeedEngagementRow metrics={p.metrics} liked={liked} onLike={onLike} />
      </div>
    </article>
  );
}

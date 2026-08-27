import { useState } from 'react';
import FeedPostCard from './FeedPostCard.jsx';
import { feedPosts } from '../fixtures.js';

export default { title: 'Phone/FeedPostCard', component: FeedPostCard, parameters: { layout: 'centered' } };

const frame = (child) => (
  <div style={{ width: 380, background: '#000', borderRadius: 16, overflow: 'hidden' }}>{child}</div>
);

// A brand score-alert post with an embedded game reference.
export const BrandWithGame = { render: () => frame(<FeedPostCard post={feedPosts[0]} />) };

// An insider post that references its own article (opens the reader on tap).
export const InsiderWithArticle = {
  render: () => frame(<FeedPostCard post={feedPosts[1]} onText={({ name }) => alert(`DM ${name}`)} onOpenArticle={() => alert('open reader')} />),
};

// A rival fan quote-posting a brand alert.
export const QuotePost = { render: () => frame(<FeedPostCard post={feedPosts[4]} />) };

// A reply, indented under its parent, with a live like toggle.
export const ReplyLikeable = {
  render: () => {
    const [liked, setLiked] = useState(false);
    return frame(
      <FeedPostCard
        post={feedPosts[3]}
        reply
        replyingTo="ESPNCFB"
        liked={liked}
        onLike={() => setLiked((v) => !v)}
      />,
    );
  },
};

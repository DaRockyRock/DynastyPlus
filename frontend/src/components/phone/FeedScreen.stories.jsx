import { useState } from 'react';
import FeedScreen from './FeedScreen.jsx';
import { feedPosts, breakingFeedPosts } from '../fixtures.js';

// FeedScreen normally reads the timeline from AppContext; the stories pass posts
// and callbacks as props so it renders standalone with fixtures.
export default { title: 'Phone/FeedScreen', component: FeedScreen, parameters: { layout: 'centered' } };

export const Timeline = {
  render: () => {
    const [likes, setLikes] = useState({});
    return (
      <div style={{ width: 394, height: 720, background: '#000', borderRadius: 28, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <FeedScreen
          posts={feedPosts}
          likes={likes}
          week={2}
          onSeen={() => {}}
          onLike={(id) => setLikes((l) => ({ ...l, [id]: !l[id] }))}
          onText={({ name }) => alert(`DM ${name}`)}
          onOpenArticle={() => alert('open reader')}
        />
      </div>
    );
  },
};

// The posts arrive out of time order (the most recent one sits in the MIDDLE of
// the array). The feed renders strictly in post-time order, newest first, so the
// timeline comes out sorted by recency regardless of incoming order.
export const SortedByRecency = {
  render: () => {
    const [likes, setLikes] = useState({});
    return (
      <div style={{ width: 394, height: 720, background: '#000', borderRadius: 28, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <FeedScreen
          posts={breakingFeedPosts}
          likes={likes}
          week={2}
          onSeen={() => {}}
          onLike={(id) => setLikes((l) => ({ ...l, [id]: !l[id] }))}
          onText={({ name }) => alert(`DM ${name}`)}
          onOpenArticle={() => alert('open reader')}
        />
      </div>
    );
  },
};

export const Empty = {
  render: () => (
    <div style={{ width: 394, height: 400, background: '#000', borderRadius: 28, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      <FeedScreen posts={[]} likes={{}} week={2} onSeen={() => {}} />
    </div>
  ),
};

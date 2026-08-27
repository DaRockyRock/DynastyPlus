import { useState } from 'react';
import FeedEngagementRow from './FeedEngagementRow.jsx';

export default { title: 'Phone/FeedEngagementRow', component: FeedEngagementRow, parameters: { layout: 'centered' } };

export const Interactive = {
  render: () => {
    const [liked, setLiked] = useState(false);
    return (
      <div style={{ width: 320, background: '#000', padding: 14, borderRadius: 12 }}>
        <FeedEngagementRow metrics={{ likes: 2800, reposts: 410, replies: 230 }} liked={liked} onLike={() => setLiked((v) => !v)} />
      </div>
    );
  },
};

export const FanPost = {
  render: () => (
    <div style={{ width: 320, background: '#000', padding: 14, borderRadius: 12 }}>
      <FeedEngagementRow metrics={{ likes: 42, reposts: 3, replies: 8 }} />
    </div>
  ),
};

import FeedQuotedPost from './FeedQuotedPost.jsx';
import { quotedPost } from '../fixtures.js';

export default { title: 'Phone/FeedQuotedPost', component: FeedQuotedPost, parameters: { layout: 'centered' } };

export const Default = {
  render: () => (
    <div style={{ width: 340, background: '#000', padding: 14, borderRadius: 12 }}>
      <FeedQuotedPost quoted={quotedPost} />
    </div>
  ),
};

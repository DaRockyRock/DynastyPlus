import FeedAuthor from './FeedAuthor.jsx';
import { feedPost } from '../fixtures.js';

export default { title: 'Phone/FeedAuthor', component: FeedAuthor, parameters: { layout: 'centered' } };

const wrap = (child) => (
  <div style={{ width: 340, background: '#000', padding: 14, borderRadius: 12 }}>{child}</div>
);

export const VerifiedBrand = { render: () => wrap(<FeedAuthor post={feedPost} />) };

export const TextableMedia = {
  render: () => wrap(
    <FeedAuthor
      post={{ author_name: 'Pete Thamel', handle: 'petethamel', verified: true, textable: true, text_kind: 'media', timestamp: '9h ago' }}
      onText={({ name }) => alert(`Open DM with ${name}`)}
    />,
  ),
};

export const Fan = {
  render: () => wrap(
    <FeedAuthor post={{ author_name: 'Husker Diehard', handle: 'huskerdiehard42', verified: false, textable: false, timestamp: '6h ago' }} />,
  ),
};

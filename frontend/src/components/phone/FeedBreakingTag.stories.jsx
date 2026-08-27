import FeedBreakingTag from './FeedBreakingTag.jsx';
import FeedPostCard from './FeedPostCard.jsx';

export default { title: 'Phone/FeedBreakingTag', component: FeedBreakingTag, parameters: { layout: 'centered' } };

const frame = (child) => (
  <div style={{ width: 380, background: '#000', borderRadius: 16, overflow: 'hidden', padding: 4 }}>{child}</div>
);

// The flag on its own.
export const Tag = { render: () => <div style={{ background: '#000', padding: 16 }}><FeedBreakingTag /></div> };

// In context: a reporter breaking what the coach just leaked, the way the world
// engine renders it at the top of the feed.
export const OnABreakingPost = {
  render: () => frame(
    <FeedPostCard
      post={{
        id: 'demo:break', author_name: 'Joel Klatt', handle: 'joelklatt', avatar: 'JK',
        verified: true, kind: 'personality', textable: true, text_kind: 'media', breaking: true,
        text: 'Sources: Garrett Mason is finalizing a move to Alabama and is expected to leave Nebraska. A search at Nebraska would follow.',
        metrics: { likes: 18400, reposts: 5200, replies: 3100 }, timestamp: 'now',
      }}
      onText={({ name }) => alert(`DM ${name}`)}
    />,
  ),
};

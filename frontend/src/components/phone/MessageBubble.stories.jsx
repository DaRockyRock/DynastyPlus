import MessageBubble from './MessageBubble.jsx';

export default { title: 'Phone/MessageBubble', component: MessageBubble, parameters: { layout: 'centered' } };

export const Conversation = {
  render: () => (
    <div className="thread" style={{ width: 360, background: '#000', borderRadius: 16, padding: 16 }}>
      <MessageBubble from="me" text="We want you here. You would be the guy from day one." tail />
      <MessageBubble from="them" text="appreciate the love coach 🙏" />
      <MessageBubble from="them" text="fired up for the visit this weekend" tail />
      <MessageBubble from="me" text="Let's make it official." tail />
    </div>
  ),
};

export const SingleBubbles = {
  render: () => (
    <div className="thread" style={{ width: 360, background: '#000', borderRadius: 16, padding: 16 }}>
      <MessageBubble from="them" text="Incoming gray bubble with a tail." tail />
      <MessageBubble from="me" text="Outgoing blue bubble with a tail." tail />
    </div>
  ),
};

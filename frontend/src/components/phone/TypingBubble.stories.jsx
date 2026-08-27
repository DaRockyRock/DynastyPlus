import TypingBubble from './TypingBubble.jsx';

export default { title: 'Phone/TypingBubble', component: TypingBubble, parameters: { layout: 'centered' } };

export const Default = {
  render: () => (
    <div className="thread" style={{ width: 360, background: '#000', borderRadius: 16, padding: 16 }}>
      <TypingBubble />
    </div>
  ),
};

// Compact version shown in a Messages list row while a contact is composing a
// reply the coach has not opened yet.
export const Inline = {
  render: () => (
    <div style={{ width: 360, background: '#000', borderRadius: 16, padding: 16 }}>
      <TypingBubble variant="inline" />
    </div>
  ),
};

import { useState } from 'react';
import PhoneBottomNav from './PhoneBottomNav.jsx';

export default { title: 'Phone/PhoneBottomNav', component: PhoneBottomNav, parameters: { layout: 'centered' } };

export const Interactive = {
  render: () => {
    const [active, setActive] = useState('messages');
    return (
      <div style={{ width: 360, background: '#000', borderRadius: 16, overflow: 'hidden' }}>
        <PhoneBottomNav active={active} onSelect={setActive} unreadMessages={3} unseenFeed={12} />
      </div>
    );
  },
};

export const FeedActive = {
  render: () => (
    <div style={{ width: 360, background: '#000', borderRadius: 16, overflow: 'hidden' }}>
      <PhoneBottomNav active="feed" unreadMessages={0} unseenFeed={47} />
    </div>
  ),
};

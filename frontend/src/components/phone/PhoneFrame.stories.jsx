import { useState } from 'react';
import PhoneFrame from './PhoneFrame.jsx';
import PhoneTabs from './PhoneTabs.jsx';
import ContactRow from './ContactRow.jsx';

const contacts = [
  { id: 'a', name: 'Cam Brooks-Lee', avatar: 'CB', category: 'Recruits', time: '9:41 AM', preview: 'appreciate the love coach, big visit this weekend' },
  { id: 'b', name: 'Coach Salomone', avatar: 'RS', category: 'Staff', time: '8:12 AM', preview: 'tempo plan is dialed for Saturday. we push the pace early.' },
  { id: 'c', name: 'Marcus Whitfield', avatar: 'MW', category: 'Players', time: '7:55 AM', preview: 'all good coach. just focused on the game plan.' },
  { id: 'd', name: 'Priya Anand', avatar: 'PA', category: 'Media', time: '10:20 AM', preview: 'hearing things on that job we talked about... 👀' },
  { id: 'e', name: 'DeShawn Carter', avatar: 'DC', category: 'Players', time: 'Yesterday', preview: 'feeling fresh coach, give me the rock 😤' },
];
const tabs = ['All', 'Staff', 'Players', 'Recruits', 'Media'];

export default { title: 'Phone/PhoneFrame', component: PhoneFrame, parameters: { layout: 'centered' } };

export const MessagesScreen = {
  render: () => {
    function Demo() {
      const [tab, setTab] = useState('All');
      const visible = tab === 'All' ? contacts : contacts.filter((c) => c.category === tab);
      return (
        <PhoneFrame>
          <div className="msg-screen">
            <div className="msg-titlebar"><span className="msg-title">Messages</span><button className="msg-edit">Done</button></div>
            <div className="msg-search">Search</div>
            <PhoneTabs tabs={tabs} active={tab} onSelect={setTab} />
            <div className="contact-list">
              {visible.map((c) => <ContactRow key={c.id} contact={c} />)}
            </div>
          </div>
        </PhoneFrame>
      );
    }
    return <Demo />;
  },
};

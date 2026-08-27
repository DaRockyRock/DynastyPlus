import { useState } from 'react';
import PhoneThread from './PhoneThread.jsx';
import PhoneFrame from './PhoneFrame.jsx';

const contact = { id: 'a', name: 'Cam Brooks-Lee', avatar: 'CB' };

export default { title: 'Phone/PhoneThread', component: PhoneThread, parameters: { layout: 'centered' } };

// A roster player's thread: the header carries the class year + depth role line
// under the name and the clarified Portal Risk chip in the budget strip.
export const Player = {
  render: () => (
    <PhoneFrame>
      <PhoneThread
        contact={{ id: 'rb', name: 'DeShawn Carter', avatar: 'DC' }}
        marker={{
          kind: 'player', id: 'deshawn_carter', name: 'DeShawn Carter', year: 'SO', position: 'RB',
          depth_chart_slot: 'Starting Running Back', expected_nil: 400000, current_nil: 420000,
          risk_of_leaving: 12, dealbreaker: 'Playing Time',
        }}
        messages={[
          { from: 'them', text: "Coach, just wanted to make sure we got time for our RBs in the gameplan this week. Bobcats' D is gonna try and pack it inside, but I think I've got a few moves that can create some space" },
        ]}
        onSend={() => {}}
        onBack={() => {}}
        onOffer={() => {}}
      />
    </PhoneFrame>
  ),
};

export const Interactive = {
  render: () => {
    function Demo() {
      const [messages, setMessages] = useState([
        { from: 'me', text: 'We want you here.' },
        { from: 'them', text: 'appreciate the love coach 🙏' },
        { from: 'them', text: 'big visit this weekend' },
      ]);
      const [typing, setTyping] = useState(false);
      const onSend = (t) => {
        setMessages((m) => [...m, { from: 'me', text: t }]);
        setTyping(true);
        setTimeout(() => {
          setTyping(false);
          setMessages((m) => [...m, { from: 'them', text: 'got it coach 👀' }]);
        }, 900);
      };
      return (
        <PhoneFrame>
          <PhoneThread contact={contact} messages={messages} typing={typing} onSend={onSend} onBack={() => {}} />
        </PhoneFrame>
      );
    }
    return <Demo />;
  },
};

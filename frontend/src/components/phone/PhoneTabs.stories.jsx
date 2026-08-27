import { useState } from 'react';
import PhoneTabs from './PhoneTabs.jsx';

const tabs = ['All', 'Staff', 'Players', 'Recruits', 'Media'];

export default { title: 'Phone/PhoneTabs', component: PhoneTabs, parameters: { layout: 'centered' } };

export const Interactive = {
  render: () => {
    function Demo() {
      const [active, setActive] = useState('All');
      return (
        <div style={{ width: 360, background: '#000', borderRadius: 16, padding: 8 }}>
          <PhoneTabs tabs={tabs} active={active} onSelect={setActive} />
        </div>
      );
    }
    return <Demo />;
  },
};

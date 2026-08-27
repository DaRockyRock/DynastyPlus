import { useState } from 'react';
import NavTabs from './NavTabs.jsx';

const tabs = [
  { id: 'home', label: 'Home' },
  { id: 'news', label: 'News Feed' },
  { id: 'cfp', label: 'CFP Committee' },
  { id: 'recruiting', label: 'Recruiting' },
  { id: 'portal', label: 'Portal' },
  { id: 'hotseat', label: 'Hot Seat' },
  { id: 'awards', label: 'Awards' },
  { id: 'archive', label: 'Archive' },
];

export default {
  title: 'Layout/NavTabs',
  component: NavTabs,
  parameters: { layout: 'fullscreen' },
};

export const Interactive = {
  render: () => {
    function Demo() {
      const [active, setActive] = useState('home');
      return <NavTabs tabs={tabs} active={active} onSelect={setActive} />;
    }
    return <Demo />;
  },
};

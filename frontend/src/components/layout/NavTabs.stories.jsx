import { useState } from 'react';
import NavTabs from './NavTabs.jsx';

const tabs = [
  { id: 'season', label: 'Season' },
  { id: 'customize', label: 'Customize' },
  { id: 'nil', label: 'NIL' },
  { id: 'recruiting', label: 'Recruiting' },
];

export default {
  title: 'Layout/NavTabs',
  component: NavTabs,
  parameters: { layout: 'fullscreen' },
};

export const Interactive = {
  render: () => {
    function Demo() {
      const [active, setActive] = useState('season');
      return <NavTabs tabs={tabs} active={active} onSelect={setActive} />;
    }
    return <Demo />;
  },
};

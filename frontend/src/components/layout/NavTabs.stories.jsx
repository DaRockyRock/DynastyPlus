import { useState } from 'react';
import NavTabs from './NavTabs.jsx';

const tabs = [
  { id: 'conferences', label: 'Conferences' },
  { id: 'schedule', label: 'Schedule' },
  { id: 'playoff-format', label: 'Playoff Format' },
  { id: 'playoff-bracket', label: 'Playoff Bracket' },
  { id: 'bowls', label: 'Bowl Games' },
  { id: 'rankings', label: 'Rankings' },
  { id: 'recruiting', label: 'Recruiting Tool' },
];

export default {
  title: 'Layout/NavTabs',
  component: NavTabs,
  parameters: { layout: 'fullscreen' },
};

export const Interactive = {
  render: () => {
    function Demo() {
      const [active, setActive] = useState('conferences');
      return <NavTabs tabs={tabs} active={active} onSelect={setActive} />;
    }
    return <Demo />;
  },
};

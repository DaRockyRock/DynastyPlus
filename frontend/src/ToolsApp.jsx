import { useState } from 'react';
import { ToolsProvider, useTools } from './context/ToolsContext.jsx';
import { ToolsTopBar, NavTabs, Toast } from './components/index.js';

import SimDashboardPage from './pages/SimDashboardPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import NilPage from './pages/NilPage.jsx';
import SimRecruitingPage from './pages/SimRecruitingPage.jsx';

const TABS = [
  { id: 'dashboard', label: 'Season', Page: SimDashboardPage },
  { id: 'customize', label: 'Customize', Page: SettingsPage },
  { id: 'nil', label: 'NIL', Page: NilPage },
  { id: 'recruiting', label: 'Recruiting', Page: SimRecruitingPage },
];

function ToolsShell({ active, setActive }) {
  const { ready, team, sim, toastMsg } = useTools();

  if (!ready) {
    return <div className="view"><div className="empty-state">Loading Dynasty+ Tools...</div></div>;
  }

  const ActivePage = (TABS.find((tab) => tab.id === active) || TABS[0]).Page;

  return (
    <>
      <ToolsTopBar team={team} sim={sim} />
      <NavTabs
        tabs={TABS}
        active={active}
        onSelect={(id) => { setActive(id); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
      />
      <main className="view">
        <ActivePage />
      </main>
      <Toast message={toastMsg} />
    </>
  );
}

export default function ToolsApp() {
  const [active, setActive] = useState('dashboard');
  return (
    <ToolsProvider setActive={setActive}>
      <ToolsShell active={active} setActive={setActive} />
    </ToolsProvider>
  );
}

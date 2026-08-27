import { useState } from 'react';
import { SimProvider } from './context/SimContext.jsx';
import { useApp } from './context/AppContext.jsx';
import { SimTopBar, NavTabs, Toast } from './components/index.js';

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

function SimShell({ active, setActive }) {
  const { ready, team, sim, pending, toastMsg } = useApp();

  if (!ready) {
    return <div className="view"><div className="empty-state">Loading Simulator...</div></div>;
  }

  const ActivePage = (TABS.find((t) => t.id === active) || TABS[0]).Page;

  return (
    <>
      <SimTopBar team={team} sim={sim} pending={(pending || []).length} onPendingClick={() => setActive('dashboard')} />
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

export default function SimulatorApp() {
  const [active, setActive] = useState('dashboard');
  return (
    <SimProvider active={active} setActive={setActive}>
      <SimShell active={active} setActive={setActive} />
    </SimProvider>
  );
}

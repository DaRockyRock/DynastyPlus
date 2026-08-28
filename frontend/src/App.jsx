import { useEffect } from 'react';
import { AppProvider, useApp } from './context/AppContext.jsx';
import { APP_NAME } from './lib/app.js';
import { TopBar, NavTabs, HintBar, LoadingOverlay, Toast, TeamBackdrop, WeekSyncModal } from './components/index.js';

import ConferenceSetupPage from './pages/ConferenceSetupPage.jsx';
import PollsPage from './pages/PollsPage.jsx';
import PlayoffToolPage from './pages/PlayoffToolPage.jsx';
import SchedulePage from './pages/SchedulePage.jsx';
import PlayoffLivePage from './pages/PlayoffLivePage.jsx';
import BowlGamesPage from './pages/BowlGamesPage.jsx';
import RecruitingToolPage from './pages/RecruitingToolPage.jsx';
import SetupPage from './pages/SetupPage.jsx';
import LandingPage from './pages/LandingPage.jsx';

const TABS = [
  { id: 'conferences', label: 'Conferences', Page: ConferenceSetupPage },
  { id: 'schedule', label: 'Schedule', Page: SchedulePage },
  { id: 'playoff', label: 'Playoff Format', Page: PlayoffToolPage },
  { id: 'bracket', label: 'Playoff Bracket', Page: PlayoffLivePage },
  { id: 'bowls', label: 'Bowl Games', Page: BowlGamesPage },
  { id: 'polls', label: 'Rankings', Page: PollsPage },
  { id: 'recruiting', label: 'Recruiting Tool', Page: RecruitingToolPage },
];

function Shell() {
  const { dynasty, ready, enteredDynasty, bowlGamesReady, pointer, mode, watcherActive, loading, toastMsg, scanNow, scanning, exitDynasty, setupOpen, activeTab, setActiveTab, autosyncEnabled, autosyncBusy, setAutosync, saveAutomation, continueSaveAutomation } = useApp();
  const active = activeTab;
  const setActive = setActiveTab;
  const tabs = TABS.filter((tab) => tab.id !== 'bowls' || bowlGamesReady);

  useEffect(() => { document.title = APP_NAME; }, []);
  useEffect(() => {
    if (active === 'bowls' && !bowlGamesReady) {
      setActive(TABS.find((tab) => tab.id !== 'bowls')?.id || 'home');
    }
  }, [active, bowlGamesReady, setActive]);

  if (!ready) {
    return <div className="view"><div className="empty-state">Loading {APP_NAME}...</div></div>;
  }

  // First-run setup (game art + folders) takes over the whole screen, before
  // anything else: the app needs the saves folder and the
  // game art. Auto-opens until set up; skippable, and reopenable from Library.
  if (setupOpen) {
    return <SetupPage />;
  }

  // Until a dynasty is entered (Scan + Continue), show the dynasty library.
  // The overlay rides along so entering a dynasty can generate the full week
  // behind a blocking progress screen before the tabs appear.
  if (!enteredDynasty || !dynasty) {
    return (
      <>
        <LandingPage />
        <LoadingOverlay
          active={loading.active}
          week={loading.week}
          team={dynasty?.team}
          progress={loading.progress}
          total={loading.total}
          module={loading.module}
          subStep={loading.subStep}
          title={loading.title}
          caption={loading.caption}
        />
        <WeekSyncModal status={saveAutomation} onContinue={continueSaveAutomation} />
      </>
    );
  }

  const ActivePage = (tabs.find((t) => t.id === active) || tabs[0]).Page;

  const hints = [
    { glyph: 's', key: 'S', label: scanning ? 'Scanning...' : 'Scan Save', onClick: scanNow, disabled: scanning },
    { glyph: 'escape', key: 'ESC', label: 'Library', onClick: exitDynasty, dark: true },
  ];

  return (
    <>
      <TeamBackdrop espnId={dynasty.team?.espn_id} />
      <TopBar
        team={dynasty.team}
        season={dynasty.season}
        week={pointer.week}
        mode={mode}
        watcherActive={watcherActive}
        onScan={scanNow}
        scanning={scanning}
        onExit={exitDynasty}
        autosyncEnabled={autosyncEnabled}
        autosyncBusy={autosyncBusy}
        onAutosyncChange={setAutosync}
      />
      <NavTabs
        tabs={tabs}
        active={active}
        onSelect={(id) => { setActive(id); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
      />
      <main className="view view-bleed">
        <ActivePage />
      </main>
      <HintBar
        hints={hints}
        brand={`${APP_NAME.toUpperCase()} | ${dynasty.season?.week_label || ''} ${dynasty.season?.year || ''}`.trim()}
      />
      <LoadingOverlay
        active={loading.active}
        week={loading.week}
        team={dynasty.team}
        progress={loading.progress}
        total={loading.total}
        module={loading.module}
        subStep={loading.subStep}
        title={loading.title}
        caption={loading.caption}
      />
      <WeekSyncModal status={saveAutomation} onContinue={continueSaveAutomation} />
      <Toast message={toastMsg} />
    </>
  );
}

export default function App() {
  return (
    <AppProvider>
      <Shell />
    </AppProvider>
  );
}

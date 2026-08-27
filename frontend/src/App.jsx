import { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext.jsx';
import { TopBar, NavTabs, LoadingOverlay, Toast, PhoneApp, ArticleReader, SettingsFab, PresserModal } from './components/index.js';

import HomePage from './pages/HomePage.jsx';
import GameCenterPage from './pages/GameCenterPage.jsx';
import NewsPage from './pages/NewsPage.jsx';
import CFPPage from './pages/CFPPage.jsx';
import RecruitingPage from './pages/RecruitingPage.jsx';
import NilPage from './pages/NilPage.jsx';
import PortalPage from './pages/PortalPage.jsx';
import HotSeatPage from './pages/HotSeatPage.jsx';
import AwardsPage from './pages/AwardsPage.jsx';
import ArchivePage from './pages/ArchivePage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import OnboardingPage from './pages/OnboardingPage.jsx';
import LandingPage from './pages/LandingPage.jsx';

const TABS = [
  { id: 'home', label: 'Home', Page: HomePage },
  { id: 'gamecenter', label: 'Game Center', Page: GameCenterPage },
  { id: 'news', label: 'News Feed', Page: NewsPage },
  { id: 'cfp', label: 'CFP Committee', Page: CFPPage },
  { id: 'recruiting', label: 'Recruiting', Page: RecruitingPage },
  { id: 'nil', label: 'NIL', Page: NilPage },
  { id: 'portal', label: 'Portal', Page: PortalPage },
  { id: 'hotseat', label: 'Hot Seat', Page: HotSeatPage },
  { id: 'awards', label: 'Awards', Page: AwardsPage },
  { id: 'archive', label: 'Archive', Page: ArchivePage },
];

function Shell() {
  const { dynasty, ready, enteredDynasty, pointer, mode, watcherActive, loading, toastMsg, openPhone, unreadTotal, scanNow, scanning, exitDynasty, article, closeArticle, settingsOpen, openSettings, onboardingOpen, openOnboarding, llm, pendingActions, activeTab, setActiveTab, presser, submitInterviewAnswer, skipInterview, closePresser } = useApp();
  const active = activeTab;
  const setActive = setActiveTab;
  const [presserBusy, setPresserBusy] = useState(false);
  const onPresserAnswer = async (text) => { setPresserBusy(true); try { await submitInterviewAnswer(text); } finally { setPresserBusy(false); } };
  const onPresserSkip = async () => { setPresserBusy(true); try { await skipInterview(); } finally { setPresserBusy(false); } };

  if (!ready) {
    return <div className="view"><div className="empty-state">Loading Dynasty+ Tools...</div></div>;
  }

  // First-run / re-entry LLM setup takes over the whole screen.
  if (onboardingOpen) {
    return <OnboardingPage />;
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
      </>
    );
  }

  if (settingsOpen) {
    return <SettingsPage />;
  }

  const tabs = TABS;
  const ActivePage = (tabs.find((t) => t.id === active) || tabs[0]).Page;

  return (
    <>
      <TopBar
        team={dynasty.team}
        season={dynasty.season}
        week={pointer.week}
        mode={mode}
        watcherActive={watcherActive}
        onScan={scanNow}
        scanning={scanning}
        onExit={exitDynasty}
        onPhone={openPhone}
        phoneUnread={unreadTotal}
        pending={pendingActions}
        onPendingClick={openPhone}
        llm={llm}
        onLLMClick={openOnboarding}
      />
      <NavTabs
        tabs={tabs}
        active={active}
        onSelect={(id) => { setActive(id); closeArticle(); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
      />
      <main className="view">
        {article ? <ArticleReader article={article} onBack={closeArticle} /> : <ActivePage />}
      </main>

      <PhoneApp />
      <PresserModal
        presser={presser}
        coachName={dynasty.team?.head_coach?.name || 'Coach'}
        busy={presserBusy}
        onAnswer={onPresserAnswer}
        onSkip={onPresserSkip}
        onClose={closePresser}
      />
      <SettingsFab onClick={openSettings} />
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

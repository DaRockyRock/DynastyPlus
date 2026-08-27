import TopBar from './TopBar.jsx';

const team = {
  name: 'Nebraska Cornhuskers', abbreviation: 'NEB', espn_id: 158, color: 'e41c38',
  conference: 'Big Ten',
  record: { overall: '8-1', conference: '5-1' },
  head_coach: { name: 'Garrett Mason' },
  rankings: { cfp: 5, ap: 5 },
};
const season = { year: 2026, week: 10, week_label: 'Week 10' };

export default {
  title: 'Layout/TopBar',
  component: TopBar,
  parameters: { layout: 'fullscreen' },
};

// Passive default - watcher connected, no manual advance control.
export const Live = {
  render: () => <TopBar team={team} season={season} week={10} mode="live" watcherActive onSync={() => {}} />,
};

// Live mode with no save detected yet - LiveStatus shows the waiting state.
export const LiveWaiting = {
  render: () => <TopBar team={team} season={season} week={10} mode="live" watcherActive={false} onSync={() => {}} />,
};

// Demo mode - manual stepper + Advance Week button for UI testing.
export const Demo = {
  render: () => <TopBar team={team} season={season} week={10} mode="demo" onAdvance={() => {}} onPrevWeek={() => {}} />,
};

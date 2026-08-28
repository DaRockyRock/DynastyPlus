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

// Watcher connected to the selected save.
export const Live = {
  render: () => <TopBar team={team} season={season} week={10} mode="live" watcherActive onSync={() => {}} />,
};

// With the global auto-sync toggle shown at the top-right.
export const WithAutosyncToggle = {
  render: () => (
    <TopBar team={team} season={season} week={10} mode="live" watcherActive
      onSync={() => {}} autosyncEnabled onAutosyncChange={() => {}} />
  ),
};

// Live mode with no save detected yet - LiveStatus shows the waiting state.
export const LiveWaiting = {
  render: () => <TopBar team={team} season={season} week={10} mode="live" watcherActive={false} onSync={() => {}} />,
};

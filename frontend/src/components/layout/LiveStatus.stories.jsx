import LiveStatus from './LiveStatus.jsx';

export default {
  title: 'Layout/LiveStatus',
  component: LiveStatus,
  parameters: { layout: 'centered' },
};

// Watcher connected to a live dynasty save.
export const Live = { args: { active: true, onSync: () => {} } };

// No save file found yet - the app waits and offers a manual refresh.
export const Waiting = { args: { active: false, onSync: () => {} } };

// Custom detail line (e.g. surfacing the watched filename).
export const WithDetail = { args: { active: true, detail: 'dynasty_huskers.sav', onSync: () => {} } };

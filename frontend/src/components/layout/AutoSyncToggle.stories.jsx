import AutoSyncToggle from './AutoSyncToggle.jsx';

export default {
  title: 'Layout/AutoSyncToggle',
  component: AutoSyncToggle,
};

export const On = { args: { enabled: true } };
export const Off = { args: { enabled: false } };
export const Busy = { args: { enabled: true, busy: true } };

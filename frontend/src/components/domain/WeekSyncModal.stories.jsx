import WeekSyncModal from './WeekSyncModal.jsx';

export default {
  title: 'Domain/WeekSyncModal',
  component: WeekSyncModal,
  parameters: { layout: 'fullscreen' },
};

export const Auditing = {
  args: { status: { phase: 'recruiting', running: true, progress: 52, save: 'DYNASTY-AUTOSAVE', message: 'Applying corrections in memory' } },
};

export const WeeklyTools = {
  args: { status: { phase: 'tools', running: true, progress: 78, save: 'DYNASTY-AUTOSAVE', message: 'Synchronizing playoff and rankings tools' } },
};

export const ReloadRequired = {
  args: {
    status: { phase: 'reload_required', reload_required: true, progress: 100, save: 'DYNASTY-AUTOSAVE', message: 'Reload this dynasty in CFB 27 before continuing' },
    onContinue: () => {},
  },
};

export const Error = {
  args: { status: { phase: 'error', message: 'The recruiting records did not pass verification.' }, onContinue: () => {} },
};

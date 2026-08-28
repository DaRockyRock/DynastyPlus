import LoadingOverlay from './LoadingOverlay.jsx';

const team = { name: 'Nebraska Cornhuskers', abbreviation: 'NEB', espn_id: 158, color: 'e41c38' };

export default {
  title: 'Layout/LoadingOverlay',
  component: LoadingOverlay,
  parameters: { layout: 'fullscreen' },
};

export const ReadingSave = {
  args: { active: true, week: 11, team, progress: 4, total: 9, module: 'save', subStep: 'Reading dynasty tables' },
};

export const UpdatingPlayoff = {
  args: { active: true, week: 11, team, progress: 9, total: 12, module: 'playoff', subStep: 'Validating bracket slots' },
};

export const NoSubStep = {
  args: { active: true, week: 3, team, progress: 1, total: 12, module: 'schedule', subStep: 'Checking protected rivals' },
};

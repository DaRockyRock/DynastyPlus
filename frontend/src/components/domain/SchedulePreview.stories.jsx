import SchedulePreview from './SchedulePreview.jsx';
import { schedulePreview, scheduleSetupState } from '../fixtures.js';

export default {
  title: 'Domain/SchedulePreview',
  component: SchedulePreview,
  parameters: { layout: 'padded' },
};

// opens on the user's first game week; the rail switches weeks
export const GeneratedSeason = {
  render: () => (
    <div style={{ width: 640 }}>
      <SchedulePreview preview={schedulePreview} userTeam={scheduleSetupState.user_team} />
    </div>
  ),
};
export const LockedWeekSelected = {
  render: () => (
    <div style={{ width: 640 }}>
      <SchedulePreview
        preview={schedulePreview}
        userTeam={scheduleSetupState.user_team}
        defaultWeek={schedulePreview.weeks.find((w) => w.locked)?.week
          ?? schedulePreview.weeks[schedulePreview.weeks.length - 1].week}
      />
    </div>
  ),
};

import { useState } from 'react';
import ScheduleRivalryRow from './ScheduleRivalryRow.jsx';
import { scheduleTeams, scheduleSetupState } from '../fixtures.js';

export default {
  title: 'Domain/ScheduleRivalryRow',
  component: ScheduleRivalryRow,
  parameters: { layout: 'padded' },
};

const teamOf = (name) => scheduleTeams.find((t) => t.name === name) || null;

function Demo(initial, defaultName = null) {
  const [riv, setRiv] = useState(initial);
  return (
    <div style={{ width: 960 }}>
      <ScheduleRivalryRow
        rivalry={riv}
        teamOf={teamOf}
        defaultName={defaultName}
        weeks={scheduleSetupState.weeks}
        onChange={setRiv}
        onRemove={() => {}}
      />
    </div>
  );
}

// a named rivalry (the game's own label, user-editable)
export const PrimaryRivalryWeek = {
  render: () => Demo({ a: 'Nebraska Cornhuskers', b: 'Iowa Hawkeyes', week: 14, location: 'rotate', primary: true, name: 'Heroes Game' }),
};
// no saved name: the game's own name for the pair shows as the suggestion
export const SuggestedGameName = {
  render: () => Demo(
    { a: 'Alabama Crimson Tide', b: 'Tennessee Volunteers', week: 8, location: 'home_a', primary: false, name: null },
    'Third Saturday in October',
  ),
};
// a pair the game has no rivalry for: the placeholder falls back to the matchup
export const AnyWeek = {
  render: () => Demo({ a: 'Ohio State Buckeyes', b: 'Wisconsin Badgers', week: null, location: 'rotate', primary: false, name: null }),
};

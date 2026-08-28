import { useState } from 'react';
import ConferenceScheduleCard from './ConferenceScheduleCard.jsx';
import { scheduleSetupState } from '../fixtures.js';

export default {
  title: 'Domain/ConferenceScheduleCard',
  component: ConferenceScheduleCard,
  parameters: { layout: 'padded' },
};

function Demo({ conference }) {
  const [value, setValue] = useState({
    games: conference.games,
    round_robin_divisions: conference.round_robin_divisions,
    rivalries: conference.rivalries,
  });
  return (
    <div style={{ width: 860 }}>
      <ConferenceScheduleCard
        conference={conference}
        value={value}
        weeks={scheduleSetupState.weeks}
        onChange={setValue}
      />
    </div>
  );
}

export const WithRivalries = {
  render: () => <Demo conference={scheduleSetupState.conferences[0]} />,
};
export const WithDivisions = {
  render: () => <Demo conference={scheduleSetupState.conferences[1]} />,
};

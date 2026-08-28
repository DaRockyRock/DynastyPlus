import { useState } from 'react';
import NonConRivalsCard from './NonConRivalsCard.jsx';
import { scheduleTeams, scheduleSetupState } from '../fixtures.js';

export default {
  title: 'Domain/NonConRivalsCard',
  component: NonConRivalsCard,
  parameters: { layout: 'padded' },
};

const conferenceNames = scheduleSetupState.conferences.map((c) => c.name);

function Demo({ initial }) {
  const [value, setValue] = useState(initial);
  return (
    <div style={{ width: 880 }}>
      <NonConRivalsCard
        teams={scheduleTeams}
        value={value}
        weeks={scheduleSetupState.weeks}
        conferenceNames={conferenceNames}
        maxPerTeam={2}
        onChange={setValue}
      />
    </div>
  );
}

export const WithRivals = {
  render: () => (
    <Demo initial={[
      { a: 'Nebraska Cornhuskers', b: 'Alabama Crimson Tide', rank: 1, week: null, location: 'rotate' },
      { a: 'Notre Dame Fighting Irish', b: 'Georgia Bulldogs', rank: 2, week: 3, location: 'home_b' },
    ]}
    />
  ),
};

// Two independents share the "FBS Independents" pool name but have no rules
// tab, so protecting the pair here must be allowed (not redirected).
export const IndependentRivals = {
  render: () => (
    <Demo initial={[
      { a: 'Notre Dame Fighting Irish', b: 'UConn Huskies', rank: 2, week: null, location: 'rotate' },
    ]}
    />
  ),
};

export const Empty = { render: () => <Demo initial={[]} /> };

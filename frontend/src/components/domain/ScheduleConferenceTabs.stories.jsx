import { useState } from 'react';
import ScheduleConferenceTabs, { NONCON_TAB } from './ScheduleConferenceTabs.jsx';
import { scheduleSetupState } from '../fixtures.js';

export default {
  title: 'Domain/ScheduleConferenceTabs',
  component: ScheduleConferenceTabs,
  parameters: { layout: 'padded' },
};

function Demo({ conferences, nonconCount, initial }) {
  const [active, setActive] = useState(initial);
  return (
    <div style={{ maxWidth: 860 }}>
      <ScheduleConferenceTabs
        conferences={conferences}
        nonconCount={nonconCount}
        active={active}
        onChange={setActive}
      />
    </div>
  );
}

export const TwoConferences = {
  render: () => (
    <Demo
      conferences={scheduleSetupState.conferences}
      nonconCount={scheduleSetupState.nonconference.length}
      initial="Big Ten"
    />
  ),
};

export const NonConferenceActive = {
  render: () => (
    <Demo
      conferences={scheduleSetupState.conferences}
      nonconCount={3}
      initial={NONCON_TAB}
    />
  ),
};

// a full FBS slate of conferences wraps onto a second row cleanly
export const FullLeague = {
  render: () => (
    <Demo
      conferences={[
        'ACC', 'American', 'Big 12', 'Big Ten', 'Conference USA', 'MAC',
        'Mountain West', 'Pac-12', 'SEC', 'Sun Belt',
      ].map((name) => ({ name, canonical: name, rivalries: name === 'SEC' ? [{}, {}] : [] }))}
      nonconCount={5}
      initial="Big Ten"
    />
  ),
};

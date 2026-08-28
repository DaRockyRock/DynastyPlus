import { useState } from 'react';
import WeekSelect from './WeekSelect.jsx';
import { scheduleSetupState } from '../fixtures.js';

export default {
  title: 'UI/WeekSelect',
  component: WeekSelect,
  parameters: { layout: 'padded' },
};

function Demo(props) {
  const [week, setWeek] = useState(props.value ?? null);
  return <WeekSelect {...props} value={week} onChange={setWeek} />;
}

export const AnyWeek = { render: () => <Demo value={null} /> };
export const RivalryWeek = { render: () => <Demo value={14} /> };
export const WithSaveWeeks = {
  render: () => <Demo value={8} weeks={scheduleSetupState.weeks} />,
};
export const RequiredPick = { render: () => <Demo value={5} allowAny={false} /> };

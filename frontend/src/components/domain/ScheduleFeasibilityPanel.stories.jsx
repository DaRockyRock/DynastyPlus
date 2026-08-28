import ScheduleFeasibilityPanel from './ScheduleFeasibilityPanel.jsx';
import { scheduleSetupState, scheduleSetupStateInfeasible } from '../fixtures.js';

export default {
  title: 'Domain/ScheduleFeasibilityPanel',
  component: ScheduleFeasibilityPanel,
  parameters: { layout: 'padded' },
};

export const Possible = {
  render: () => (
    <div style={{ width: 560 }}>
      <ScheduleFeasibilityPanel feasibility={scheduleSetupState.feasibility} />
    </div>
  ),
};
export const NotPossible = {
  render: () => (
    <div style={{ width: 560 }}>
      <ScheduleFeasibilityPanel feasibility={scheduleSetupStateInfeasible.feasibility} />
    </div>
  ),
};

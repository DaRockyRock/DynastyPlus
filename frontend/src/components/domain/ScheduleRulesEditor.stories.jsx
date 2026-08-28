import ScheduleRulesEditor from './ScheduleRulesEditor.jsx';
import {
  scheduleSetupState, scheduleSetupStateInfeasible, scheduleSetupStateWeek1Locked,
  schedulePreview,
} from '../fixtures.js';

export default {
  title: 'Domain/ScheduleRulesEditor',
  component: ScheduleRulesEditor,
  parameters: { layout: 'fullscreen' },
};

const stubFns = (state) => ({
  load: async () => state,
  save: async () => state,
  reset: async () => state,
  generate: async () => ({ ok: true, errors: [], warnings: [], plan: schedulePreview }),
  apply: async () => ({ ok: true, changed: 52 }),
});

export const Feasible = {
  render: () => (
    <div style={{ padding: 24 }}>
      <ScheduleRulesEditor embedded initialData={scheduleSetupState} apiFns={stubFns(scheduleSetupState)} />
    </div>
  ),
};

export const NotPossible = {
  render: () => (
    <div style={{ padding: 24 }}>
      <ScheduleRulesEditor embedded initialData={scheduleSetupStateInfeasible} apiFns={stubFns(scheduleSetupStateInfeasible)} />
    </div>
  ),
};

export const WithGeneratedPreview = {
  render: () => (
    <div style={{ padding: 24 }}>
      <ScheduleRulesEditor
        embedded
        initialData={{ ...scheduleSetupState, plan_ready: true, plan_preview: schedulePreview }}
        apiFns={stubFns(scheduleSetupState)}
      />
    </div>
  ),
};

export const GateClosed = {
  render: () => (
    <div style={{ padding: 24 }}>
      <ScheduleRulesEditor
        embedded
        initialData={{
          ...scheduleSetupState,
          apply_gate: {
            ok: false,
            phase: 'regular',
            reason: 'Games have already been played this season. The schedule can only be regenerated before any results are official, from a preseason save at the start of a season.',
          },
        }}
        apiFns={stubFns(scheduleSetupState)}
      />
    </div>
  ),
};

// the season schedule does not exist in the save yet (dynasty creation or an
// early preseason stage): the gate walks the user to a late-preseason save
export const GatePregeneration = {
  render: () => (
    <div style={{ padding: 24 }}>
      <ScheduleRulesEditor
        embedded
        initialData={{
          ...scheduleSetupState,
          apply_gate: {
            ok: false,
            phase: 'pregeneration',
            reason: 'The game has not generated this season\'s schedule yet. In CFB 27, continue through the preseason until the Week 1 schedule appears, then save while STILL in the preseason and Scan again. A preseason save has no locked weeks, so the generator can rebuild every week, including Week 1.',
          },
        }}
        apiFns={stubFns(scheduleSetupState)}
      />
    </div>
  ),
};

// a Week 1 arrival save: the opening week is pinned, the note points at the
// preseason save that lifts it (the default fixture shows the full rebuild)
export const Week1Locked = {
  render: () => (
    <div style={{ padding: 24 }}>
      <ScheduleRulesEditor
        embedded
        initialData={scheduleSetupStateWeek1Locked}
        apiFns={stubFns(scheduleSetupStateWeek1Locked)}
      />
    </div>
  ),
};

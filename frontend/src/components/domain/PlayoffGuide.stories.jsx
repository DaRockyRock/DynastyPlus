import PlayoffGuide from './PlayoffGuide.jsx';
import { playoffGuide, playoffGuideComplete } from '../fixtures.js';

export default {
  title: 'Domain/PlayoffGuide',
  component: PlayoffGuide,
  parameters: { layout: 'padded' },
};

const frame = (guide) => (
  <div style={{ maxWidth: 1100 }}>
    <PlayoffGuide guide={guide} />
  </div>
);

export const MidPlayoff = { render: () => frame(playoffGuide) };
export const NeedsUpdate = {
  render: () => frame({
    ...playoffGuide,
    phases: playoffGuide.phases.map((p) => (p.state !== 'current' ? p : {
      ...p,
      steps: p.steps.map((s) => ({
        ...s,
        state: s.id === 'update' ? 'current' : 'todo',
      })),
    })),
  }),
};
export const PreSeason = {
  render: () => frame({ mode: null, status: 'projected', phases: [playoffGuide.phases[0]].map((p) => ({
    ...p,
    state: 'current',
    steps: p.steps.map((s, i) => ({ ...s, state: i === 0 ? 'current' : 'todo',
      detail: i === 0 ? 'Play or sim through the regular season and the conference championship games.' : undefined })),
  })) })
};
export const Complete = { render: () => frame(playoffGuideComplete) };

// The recovery walkthrough shown when CFB 27 locked and simmed the playoff
// week before the app could schedule into it (a post-lock arrival save):
// the rounds wait while the user moves the dynasty to a fresh bowl week.
export const LockedWeekRecovery = {
  render: () => frame({
    ...playoffGuide,
    phases: [
      { ...playoffGuide.phases[0], state: 'done' },
      {
        key: 'anchor',
        title: 'Move to a fresh bowl week',
        state: 'current',
        steps: [{
          id: 'advance',
          label: 'Play or sim this week, then advance and exit',
          detail: 'CFB 27 locked and simmed this week\'s games before the '
            + 'playoff could schedule into it, so this week cannot host the '
            + 'bracket. In CFB 27, play or sim the week as normal, advance '
            + 'to the next bowl week, then exit to the main menu. The '
            + 'playoff sets up there automatically.',
          state: 'current',
        }],
      },
      ...playoffGuide.phases.slice(1).map((p) => ({ ...p, state: 'upcoming' })),
    ],
  }),
};

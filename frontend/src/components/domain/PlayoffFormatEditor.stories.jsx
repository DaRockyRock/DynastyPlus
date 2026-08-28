import PlayoffFormatEditor from './PlayoffFormatEditor.jsx';
import { playoffBracket12, playoffBracket24 } from '../fixtures.js';

// The editor normally talks to /api/playoff/*; stories inject initialData and
// a previewFn so the whole studio renders offline.
const bowls = [
  { key: 'peach', name: 'Peach Bowl' }, { key: 'rose', name: 'Rose Bowl' },
  { key: 'fiesta', name: 'Fiesta Bowl' }, { key: 'sugar', name: 'Sugar Bowl' },
  { key: 'cotton', name: 'Cotton Bowl' }, { key: 'orange', name: 'Orange Bowl' },
  { key: 'citrus', name: 'Citrus Bowl' }, { key: 'alamo', name: 'Alamo Bowl' },
];

const cfp12 = {
  teams: 12,
  byes: [{ teams: 4, rounds: 1 }],
  bye_selection: 'seeding',
  auto_bids: { champions: 5 },
  disqualify: { max_losses: null, losing_conf_record: false, rivalry_week_loss: false, champions_only: false, ranked_only: false },
  notre_dame_rule: true,
  sites: {
    rounds: [
      { mode: 'higher_seed', games: [] },
      { mode: 'bowls', bowls: ['peach', 'rose', 'fiesta', 'sugar'], games: [] },
      { mode: 'bowls', bowls: ['cotton', 'orange'], games: [] },
    ],
    championship: { venue: 'Mercedes-Benz Stadium', city: 'Atlanta, GA' },
  },
};

const initialData = { format: cfp12, default: cfp12, customized: false, bowls };
const previewFn = async (fmt) => ({
  bracket: fmt.teams >= 20 ? playoffBracket24 : playoffBracket12,
  problems: [],
});

export default {
  title: 'Domain/PlayoffFormatEditor',
  component: PlayoffFormatEditor,
  parameters: { layout: 'fullscreen' },
};

export const Embedded = {
  render: () => (
    <div style={{ padding: 24 }}>
      <PlayoffFormatEditor embedded initialData={initialData} previewFn={previewFn} />
    </div>
  ),
};

export const Overlay = {
  render: () => <PlayoffFormatEditor initialData={initialData} previewFn={previewFn} onClose={() => {}} />,
};

export const AutomationOff = {
  // The custom playoff is off: the whole editor collapses to the off-state
  // hero (PlayoffOffState), the switch front and center, no format controls.
  render: () => (
    <div style={{ padding: 24 }}>
      <PlayoffFormatEditor
        embedded
        initialData={{ ...initialData, enabled: false }}
        previewFn={previewFn}
      />
    </div>
  ),
};

export const WithProblems = {
  render: () => (
    <div style={{ padding: 24 }}>
      <PlayoffFormatEditor
        embedded
        initialData={{ ...initialData, format: { ...cfp12, teams: 6, byes: [] } }}
        previewFn={async () => ({
          bracket: null,
          problems: ['This bye structure does not close into a bracket: the field covers 6 opening slots, which must be a power of two (nearest are 4 and 8). Adjust the field size or the number of teams on byes.'],
        })}
      />
    </div>
  ),
};

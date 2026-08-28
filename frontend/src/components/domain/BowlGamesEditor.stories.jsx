import BowlGamesEditor from './BowlGamesEditor.jsx';
import { bowlGamesState } from '../fixtures.js';

export default { title: 'Domain/BowlGamesEditor', component: BowlGamesEditor };

const apiFns = {
  load: async () => bowlGamesState,
  apply: async () => ({ ...bowlGamesState, applied: true, written: true }),
};

export const FullSchedule = {
  render: () => <BowlGamesEditor initialData={bowlGamesState} apiFns={apiFns} />,
};

export const CompletedSeason = {
  render: () => (
    <BowlGamesEditor
      initialData={{ ...bowlGamesState, editable: false, status: 'complete' }}
      apiFns={apiFns}
    />
  ),
};

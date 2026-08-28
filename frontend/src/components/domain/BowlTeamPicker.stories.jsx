import BowlTeamPicker from './BowlTeamPicker.jsx';
import { bowlGameTeams } from '../fixtures.js';

export default { title: 'Domain/BowlTeamPicker', component: BowlTeamPicker };

export const AwayTeam = {
  args: {
    label: 'Away team',
    teams: bowlGameTeams,
    value: bowlGameTeams[0].row,
    onChange: () => {},
  },
};

import TeamMovePicker from './TeamMovePicker.jsx';
import { conferenceSetupState, conferenceTeamsByName } from '../fixtures.js';

export default {
  title: 'Domain/TeamMovePicker',
  component: TeamMovePicker,
  parameters: { layout: 'centered' },
};

export const Open = {
  render: () => (
    <TeamMovePicker
      open
      team="Clemson Tigers"
      fromId="acc"
      teamsByName={conferenceTeamsByName}
      conferences={conferenceSetupState.conferences}
      onMove={() => {}}
      onClose={() => {}}
    />
  ),
};

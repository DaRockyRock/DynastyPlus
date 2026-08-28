import DivisionEditor from './DivisionEditor.jsx';
import { conferenceSunBelt, conferenceTeamsByName } from '../fixtures.js';

export default {
  title: 'Domain/DivisionEditor',
  component: DivisionEditor,
  parameters: { layout: 'padded' },
};

export const TwoDivisions = {
  render: () => <div style={{ width: 720 }}><DivisionEditor conf={conferenceSunBelt} teamsByName={conferenceTeamsByName} onRename={() => {}} onSwap={() => {}} /></div>,
};

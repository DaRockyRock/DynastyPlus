import RivalryEditor from './RivalryEditor.jsx';
import { conferenceBigTen, conferenceAcc } from '../fixtures.js';

export default {
  title: 'Domain/RivalryEditor',
  component: RivalryEditor,
  parameters: { layout: 'padded' },
};

export const WithRivalries = {
  render: () => <div style={{ width: 640 }}><RivalryEditor conf={conferenceBigTen} onChange={() => {}} /></div>,
};

export const Empty = {
  render: () => <div style={{ width: 640 }}><RivalryEditor conf={conferenceAcc} onChange={() => {}} /></div>,
};

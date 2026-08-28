import ConferenceMemberList from './ConferenceMemberList.jsx';
import { conferenceBigTen, conferenceAtMax, conferenceUnderMin, conferenceTeamsByName } from '../fixtures.js';

export default {
  title: 'Domain/ConferenceMemberList',
  component: ConferenceMemberList,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => <div style={{ width: 560 }}><ConferenceMemberList conf={conferenceBigTen} teamsByName={conferenceTeamsByName} onMove={() => {}} /></div>,
};

export const AtCapacity = {
  render: () => <div style={{ width: 560 }}><ConferenceMemberList conf={conferenceAtMax} teamsByName={conferenceTeamsByName} onMove={() => {}} /></div>,
};

export const UnderMinimum = {
  render: () => <div style={{ width: 560 }}><ConferenceMemberList conf={conferenceUnderMin} teamsByName={conferenceTeamsByName} onMove={() => {}} /></div>,
};

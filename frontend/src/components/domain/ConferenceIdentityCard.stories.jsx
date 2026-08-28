import ConferenceIdentityCard from './ConferenceIdentityCard.jsx';
import { conferenceBigTen, conferenceIndependents, conferenceCustom, historicConferenceLogos } from '../fixtures.js';

const stub = async () => ({ url: '/game-assets/conferences/bigten.png' });

export default {
  title: 'Domain/ConferenceIdentityCard',
  component: ConferenceIdentityCard,
  parameters: { layout: 'padded' },
};

export const InGame = {
  render: () => <div style={{ width: 720 }}><ConferenceIdentityCard conf={conferenceBigTen} onUpload={stub} /></div>,
};

export const WithHistoricLogos = {
  render: () => (
    <div style={{ width: 720 }}>
      <ConferenceIdentityCard conf={conferenceBigTen} onUpload={stub} historicLogos={historicConferenceLogos.Big_Ten} />
    </div>
  ),
};

export const Independents = {
  render: () => <div style={{ width: 720 }}><ConferenceIdentityCard conf={conferenceIndependents} onUpload={stub} /></div>,
};

export const CustomConference = {
  render: () => <div style={{ width: 720 }}><ConferenceIdentityCard conf={conferenceCustom} onUpload={stub} /></div>,
};

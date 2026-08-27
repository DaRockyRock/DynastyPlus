import ConvoPeerMeta from './ConvoPeerMeta.jsx';
import { playerMarker } from '../fixtures.js';

export default {
  title: 'Phone/ConvoPeerMeta',
  component: ConvoPeerMeta,
  parameters: { layout: 'fullscreen' },
};

// Sits under the contact name in a conversation header, so preview it on the same
// dark field with a name above it for context.
const Frame = ({ name, children }) => (
  <div style={{ background: '#000', padding: 16, width: 380, textAlign: 'center', fontFamily: 'var(--font-body)' }}>
    <div className="cp-name" style={{ justifyContent: 'center' }}>{name} <span>›</span></div>
    {children}
  </div>
);

// Starter: class year + "#1 RB" depth role read from the slot text.
export const Starter = {
  render: () => (
    <Frame name="DeShawn Carter">
      <ConvoPeerMeta marker={{ kind: 'player', year: 'SO', position: 'RB', depth_chart_slot: 'Starting Running Back' }} />
    </Frame>
  ),
};

// Backup: rank word maps to "#2".
export const Backup = {
  render: () => (
    <Frame name="Cole Vermeer">
      <ConvoPeerMeta marker={{ kind: 'player', year: 'FR', position: 'TE', depth_chart_slot: 'Backup Tight End' }} />
    </Frame>
  ),
};

// Default fixture (a junior starting QB).
export const FromFixture = {
  render: () => <Frame name={playerMarker.name}><ConvoPeerMeta marker={playerMarker} /></Frame>,
};

// Non-player contacts show their plain role, so the coach always knows who he is
// texting even when there is no roster marker to read class year and depth from.
export const Recruit = {
  render: () => <Frame name="Cam Brooks-Lee"><ConvoPeerMeta contact={{ role: '5-star WR target' }} /></Frame>,
};

export const Reporter = {
  render: () => <Frame name="Jenna Whitlock"><ConvoPeerMeta contact={{ role: 'Beat writer, Cornhusker Insider' }} /></Frame>,
};

export const OpposingCoach = {
  render: () => <Frame name="Lincoln Pope"><ConvoPeerMeta contact={{ role: 'Head Coach, Florida Gators' }} /></Frame>,
};

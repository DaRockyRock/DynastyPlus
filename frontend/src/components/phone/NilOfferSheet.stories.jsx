import NilOfferSheet from './NilOfferSheet.jsx';
import { recruitMarker, playerMarker } from '../fixtures.js';

export default {
  title: 'Phone/NilOfferSheet',
  component: NilOfferSheet,
  parameters: { layout: 'fullscreen' },
};

const Frame = ({ children }) => (
  <div style={{ background: '#000', width: 380, height: 520, position: 'relative', fontFamily: 'var(--font-body)' }}>{children}</div>
);

export const Recruit = { render: () => <Frame><NilOfferSheet marker={recruitMarker} onSubmit={() => {}} onClose={() => {}} /></Frame> };
export const Player = { render: () => <Frame><NilOfferSheet marker={playerMarker} onSubmit={() => {}} onClose={() => {}} /></Frame> };

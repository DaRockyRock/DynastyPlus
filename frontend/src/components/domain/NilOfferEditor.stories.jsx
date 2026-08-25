import NilOfferEditor from './NilOfferEditor.jsx';
import { budgetSnapshot } from '../fixtures.js';

export default {
  title: 'Domain/NilOfferEditor',
  component: NilOfferEditor,
  parameters: { layout: 'padded' },
};

export const Recruit = {
  render: () => <NilOfferEditor row={budgetSnapshot.recruiting_nil[0]} kind="recruit" onSubmit={() => {}} onClose={() => {}} />,
};
export const Player = {
  render: () => <NilOfferEditor row={budgetSnapshot.roster_nil[0]} kind="player" onSubmit={() => {}} onClose={() => {}} />,
};

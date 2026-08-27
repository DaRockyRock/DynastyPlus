import OfferReceiptBubble from './OfferReceiptBubble.jsx';
import { offerReceipt, actionReceipt } from '../fixtures.js';

export default {
  title: 'Phone/OfferReceiptBubble',
  component: OfferReceiptBubble,
  parameters: { layout: 'fullscreen' },
};

const Frame = ({ children }) => (
  <div style={{ background: '#000', padding: 16, width: 380, fontFamily: 'var(--font-body)' }}>{children}</div>
);

export const Offer = { render: () => <Frame><OfferReceiptBubble effect={offerReceipt} /></Frame> };
export const Action = { render: () => <Frame><OfferReceiptBubble effect={actionReceipt} /></Frame> };
export const Failed = {
  render: () => <Frame><OfferReceiptBubble effect={{ kind: 'recruiting_action', ok: false, action_label: 'Send the House', message: 'Not enough recruiting hours left this week (300 of 600 needed).' }} /></Frame>,
};

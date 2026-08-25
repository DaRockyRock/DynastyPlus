import { useState } from 'react';
import Card from '../ui/Card.jsx';
import Button from '../ui/Button.jsx';
import MoneyValue from '../ui/MoneyValue.jsx';
import { formatMoney } from '../../lib/format.js';

// HUD-styled NIL offer editor used inside a Modal on the NIL hub page. Slider
// runs 0..2x expected (the cap for the biggest bonus); shows the Dynasty Points
// cost of the change. `kind` is 'recruit' or 'player'.
export default function NilOfferEditor({ row, kind = 'recruit', dpPerDollar = 0.0004, onSubmit, onClose }) {
  const expected = row?.expected_nil || 0;
  const isPlayer = kind === 'player';
  const current = isPlayer ? (row?.current_nil || 0) : (row?.offer || 0);
  const max = Math.max(expected * 2, current, 100000);
  const [amount, setAmount] = useState(current);

  const dpCost = Math.round((amount - current) * dpPerDollar);
  const ratio = expected ? amount / expected : 0;
  const posture = amount === 0 ? 'No offer' : amount >= expected ? 'Above' : 'Below';

  return (
    <Card className="offer-editor">
      <div className="oe-head">
        <h3>{isPlayer ? 'Adjust NIL' : 'NIL Offer'}</h3>
        <span className="oe-name">{row?.name}</span>
      </div>
      <div className="oe-amount"><MoneyValue value={amount} suffix="/yr" tone="nil" /></div>
      <input
        className="oe-slider" type="range" min="0" max={max} step="25000"
        value={amount} onChange={(e) => setAmount(+e.target.value)}
      />
      <div className="oe-stats">
        <span>Expected <b>{formatMoney(expected)}</b></span>
        <span>{posture}{expected ? ` (${ratio.toFixed(2)}x)` : ''}</span>
        <span>DP cost <b>{dpCost >= 0 ? `+${dpCost}` : dpCost}</b></span>
      </div>
      <div className="oe-actions">
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="accent" onClick={() => onSubmit?.(amount)}>{isPlayer ? 'Update Pay' : 'Send Offer'}</Button>
      </div>
    </Card>
  );
}

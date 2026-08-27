import { useState } from 'react';
import { formatMoney } from '../../lib/format.js';

// Bottom sheet for making an NIL offer inside a chat. Slider runs 0..2x the
// expected amount (the cap for the biggest weekly bonus). Shows the Dynasty
// Points cost of the change and where the offer sits vs expectation.
export default function NilOfferSheet({ marker, dpPerDollar = 0.0004, onSubmit, onClose }) {
  const expected = marker?.expected_nil || 0;
  const isPlayer = marker?.kind === 'player';
  const current = isPlayer ? (marker.current_nil || 0) : (marker.offer || 0);
  const max = Math.max(expected * 2, current, 100000);
  const [amount, setAmount] = useState(current);

  const dpCost = Math.round((amount - current) * dpPerDollar);
  const ratio = expected ? amount / expected : 0;
  const posture = amount === 0 ? 'No offer' : amount >= expected ? `Above (${ratio.toFixed(2)}x)` : `Below (${ratio.toFixed(2)}x)`;

  return (
    <div className="phone-sheet">
      <div className="ps-handle" />
      <div className="ps-title">{isPlayer ? 'Adjust NIL' : 'NIL Offer'} - {marker.name}</div>
      <div className="ps-amount">{formatMoney(amount)}<small>/yr</small></div>
      <input
        className="ps-slider" type="range" min="0" max={max} step="25000"
        value={amount} onChange={(e) => setAmount(+e.target.value)}
      />
      <div className="ps-stats">
        <span>Expected <b>{formatMoney(expected)}</b></span>
        <span>{posture}</span>
        <span>DP cost <b>{dpCost >= 0 ? `+${dpCost}` : dpCost}</b></span>
      </div>
      <div className="ps-actions">
        <button className="ps-btn" onClick={onClose}>Cancel</button>
        <button className="ps-btn primary" onClick={() => onSubmit?.(amount)}>{isPlayer ? 'Update Pay' : 'Send Offer'}</button>
      </div>
    </div>
  );
}

import { formatMoney } from '../../lib/format.js';

// An applied NIL offer / recruiting action rendered as a receipt inside the
// thread (like a payment card in iMessage). Driven by the backend `effect`.
export default function OfferReceiptBubble({ effect }) {
  if (!effect) return null;
  const isOffer = effect.kind === 'nil_offer';
  const isAction = effect.kind === 'recruiting_action';
  const isBudget = effect.kind === 'budget_request';
  const failed = isAction && effect.ok === false;

  const title = isOffer
    ? (effect.entity_kind === 'player' ? 'NIL Update' : 'NIL Offer')
    : isAction ? effect.action_label
    : isBudget ? 'Budget Talk'
    : 'Update';

  const sign = (n) => (n >= 0 ? `+${n}` : `${n}`);

  return (
    <div className={`offer-receipt${failed ? ' failed' : ''}`}>
      <div className="or-head">
        <span className="or-type">{title}</span>
        {isOffer && <span className="or-amt">{formatMoney(effect.amount)}/yr</span>}
      </div>
      {effect.message && <div className="or-body">{effect.message}</div>}
      <div className="or-meta">
        {'influence_delta' in effect && <span>Influence {sign(effect.influence_delta)}</span>}
        {'dp_cost' in effect && <span>DP {sign(effect.dp_cost)}</span>}
        {'stage' in effect && <span className="or-stage">{effect.stage}</span>}
        {'risk_of_leaving' in effect && <span>Risk {effect.risk_of_leaving}</span>}
        {isAction && 'remaining' in effect && <span>{effect.remaining} hrs left</span>}
      </div>
    </div>
  );
}

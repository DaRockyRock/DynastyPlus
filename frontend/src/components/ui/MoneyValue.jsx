import { formatMoney } from '../../lib/format.js';

// A dollar figure in the broadcast display face. `suffix` adds a small unit
// (e.g. "/yr"); `tone` tints it (pos/neg/nil) for budget context.
export default function MoneyValue({ value, suffix, tone = 'default', className = '' }) {
  return (
    <span className={['money', tone, className].filter(Boolean).join(' ')}>
      {formatMoney(value)}
      {suffix && <small>{suffix}</small>}
    </span>
  );
}

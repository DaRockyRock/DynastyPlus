import StageTag from '../ui/StageTag.jsx';
import { formatMoney, formatPoints } from '../../lib/format.js';

// The budget marker strip pinned under a conversation header. What it shows
// depends on who you are texting: a recruit, a roster player, the AD, or staff.
export default function ChatBudgetHeader({ marker }) {
  if (!marker) return null;

  if (marker.kind === 'recruit') {
    return (
      <div className="chat-budget-header">
        <StageTag stage={marker.stage} />
        <span className="cbh-chip">Offer <b>{formatMoney(marker.offer)}</b></span>
        <span className="cbh-chip">Exp {formatMoney(marker.expected_nil)}</span>
        <span className="cbh-chip">Int <b>{marker.interest}</b></span>
        <span className="cbh-chip">Hrs <b>{marker.hours_remaining}</b></span>
      </div>
    );
  }

  if (marker.kind === 'player') {
    return (
      <div className="chat-budget-header">
        <span className="cbh-chip">Paying <b>{formatMoney(marker.current_nil)}</b></span>
        <span className="cbh-chip">Exp {formatMoney(marker.expected_nil)}</span>
        <span
          className={`cbh-chip${marker.risk_of_leaving >= 50 ? ' hot' : ''}`}
          title="How likely he is to enter the transfer portal (0 to 100). Pay at or above his expected NIL to lower it."
        >
          Portal Risk <b>{marker.risk_of_leaving}</b>/100
        </span>
      </div>
    );
  }

  if (marker.kind === 'budget') {
    return (
      <div className="chat-budget-header">
        <span className="cbh-chip">DP <b>{formatPoints(marker.available_dp)}</b></span>
        <span className="cbh-chip">Recruiting {formatMoney(marker.recruiting_available)}</span>
        <span className="cbh-chip">Hrs <b>{marker.hours_remaining}</b></span>
      </div>
    );
  }

  if (marker.kind === 'staff') {
    return (
      <div className="chat-budget-header">
        <span className="cbh-chip">Recruiting Hrs <b>{marker.hours_remaining}</b> / {marker.hours_total}</span>
      </div>
    );
  }

  return null;
}

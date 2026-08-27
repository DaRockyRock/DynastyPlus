// Contextual action buttons above the message input. A recruit gets NIL +
// recruiting hours; a roster player gets a pay adjustment; the AD gets a budget
// ask. Staff and media get none (their header marker is informational only).
export default function ChatActionBar({ marker, onOffer, onRecruitingAction, onBudgetRequest }) {
  if (!marker) return null;
  const btns = [];

  if (marker.kind === 'recruit') {
    btns.push(<button key="o" className="chat-action-btn primary" onClick={onOffer}>{marker.offer > 0 ? 'Edit Offer' : 'Offer NIL'}</button>);
    btns.push(<button key="r" className="chat-action-btn" onClick={onRecruitingAction}>Recruiting</button>);
  } else if (marker.kind === 'player') {
    btns.push(<button key="o" className="chat-action-btn primary" onClick={onOffer}>Adjust NIL</button>);
  } else if (marker.kind === 'budget') {
    btns.push(<button key="b" className="chat-action-btn primary" onClick={onBudgetRequest}>Request Budget</button>);
  }

  if (!btns.length) return null;
  return <div className="chat-actions">{btns}</div>;
}

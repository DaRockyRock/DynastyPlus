import { useState, useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble.jsx';
import TypingBubble from './TypingBubble.jsx';
import ChatBudgetHeader from './ChatBudgetHeader.jsx';
import ConvoPeerMeta from './ConvoPeerMeta.jsx';
import ChatActionBar from './ChatActionBar.jsx';
import NilOfferSheet from './NilOfferSheet.jsx';
import RecruitingActionSheet from './RecruitingActionSheet.jsx';
import OfferReceiptBubble from './OfferReceiptBubble.jsx';
import { SendIcon } from '../ui/icons.jsx';

// A conversation screen: header (back + peer), an optional budget marker, the
// scrolling bubbles (incl. NIL/action receipts), contextual action buttons, and
// the iMessage-style input. NIL/recruiting actions open a bottom sheet.
export default function PhoneThread({
  contact, messages = [], typing = false, onSend, onBack,
  marker = null, actions = [], hoursRemaining = 0, dpPerDollar,
  onOffer, onRecruitingAction, onBudgetRequest,
}) {
  const [text, setText] = useState('');
  const [sheet, setSheet] = useState(null); // 'offer' | 'actions'
  const threadRef = useRef(null);

  useEffect(() => {
    if (threadRef.current) threadRef.current.scrollTop = threadRef.current.scrollHeight;
  }, [messages, typing]);

  const send = () => {
    const t = text.trim();
    if (t) { onSend?.(t); setText(''); }
  };

  const withTail = messages.map((m, i) => ({
    ...m,
    tail: i === messages.length - 1 || messages[i + 1].from !== m.from,
  }));

  return (
    <div className="convo">
      <div className="convo-header">
        <button className="convo-back" onClick={onBack} aria-label="Back">‹</button>
        <div className="convo-peer">
          <div className="cp-avatar" style={contact.image ? { overflow: 'hidden' } : undefined}>
            {contact.image
              ? <img src={contact.image} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              : contact.avatar}
          </div>
          <div className="cp-name">{contact.name} <span>›</span></div>
          <ConvoPeerMeta contact={contact} marker={marker} />
        </div>
        <div className="convo-spacer" />
      </div>

      <ChatBudgetHeader marker={marker} />

      <div className="thread" ref={threadRef}>
        <div className="day">Today</div>
        {withTail.map((m, i) => (
          m.kind === 'receipt'
            ? <OfferReceiptBubble key={i} effect={m.effect} />
            : <MessageBubble key={i} from={m.from} text={m.text} tail={m.tail} />
        ))}
        {typing && <TypingBubble />}
      </div>

      <ChatActionBar
        marker={marker}
        onOffer={() => setSheet('offer')}
        onRecruitingAction={() => setSheet('actions')}
        onBudgetRequest={onBudgetRequest}
      />

      <div className="phone-input">
        <div className="field">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') send(); }}
            placeholder="iMessage"
            autoComplete="off"
          />
          <button className="send" onClick={send} disabled={!text.trim()} aria-label="Send">
            <SendIcon size={16} />
          </button>
        </div>
      </div>

      {sheet === 'offer' && marker && (
        <NilOfferSheet
          marker={marker}
          dpPerDollar={dpPerDollar}
          onSubmit={(amount) => { onOffer?.(amount); setSheet(null); }}
          onClose={() => setSheet(null)}
        />
      )}
      {sheet === 'actions' && (
        <RecruitingActionSheet
          actions={actions}
          hoursRemaining={hoursRemaining}
          onPick={(key) => { onRecruitingAction?.(key); setSheet(null); }}
          onClose={() => setSheet(null)}
        />
      )}
    </div>
  );
}

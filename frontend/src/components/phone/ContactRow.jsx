import ContactSubtitle from './ContactSubtitle.jsx';
import UnreadDot from './UnreadDot.jsx';
import TypingBubble from './TypingBubble.jsx';

const SUBTITLE_CATEGORIES = new Set(['Staff', 'Players', 'Recruits', 'Media']);

// A Messages list row: unread dot, avatar, name, category subtitle, last-message
// preview, time, chevron. `unread` is the count of unread inbound texts. `preview`
// overrides the contact's static preview with the live thread's last message, so
// the list and the open conversation always show the same text. `typing` shows a
// live three-dot indicator while this contact is composing a reply.
export default function ContactRow({ contact, onClick, unread = 0, preview, typing = false }) {
  const c = contact;
  // A subtitle renders for the curated categories, and for anyone else who at
  // least carries a role (an opposing coach, a candidate), so the layout reserves
  // its single-line preview whenever ContactSubtitle has something to show.
  const hasSubtitle = SUBTITLE_CATEGORIES.has(c.category) || !!c.role;
  const previewText = preview != null ? preview : (c.preview || '');
  const cls = `contact${hasSubtitle ? ' has-subtitle' : ''}${unread > 0 ? ' unread' : ''}`;
  return (
    <div className={cls} onClick={onClick}>
      <UnreadDot unread={unread > 0} />
      <div className="c-avatar" style={c.image ? { overflow: 'hidden' } : undefined}>
        {c.image
          ? <img src={c.image} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          : (c.avatar || c.name.slice(0, 2))}
      </div>
      <div className="c-body">
        <div className="c-row1">
          <span className="c-name">{c.name}</span>
          <span className="c-time">{c.time || ''}</span>
        </div>
        <ContactSubtitle contact={c} />
        <div className="c-preview">{typing ? <TypingBubble variant="inline" /> : previewText}</div>
      </div>
      <span className="c-chevron">›</span>
    </div>
  );
}

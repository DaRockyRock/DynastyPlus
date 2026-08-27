import CountBadge from '../ui/CountBadge.jsx';
import { MessageIcon, FeedIcon } from '../ui/icons.jsx';

// The phone's bottom tab bar, switching between Messages and the social Feed.
// Each tab carries a count badge (unread texts / unseen posts). iOS-style.
export default function PhoneBottomNav({ active = 'messages', onSelect, unreadMessages = 0, unseenFeed = 0 }) {
  const tabs = [
    { id: 'messages', label: 'Messages', Icon: MessageIcon, count: unreadMessages },
    { id: 'feed', label: 'Feed', Icon: FeedIcon, count: unseenFeed },
  ];
  return (
    <nav className="phone-bottom-nav">
      {tabs.map(({ id, label, Icon, count }) => (
        <button
          key={id}
          type="button"
          className={`phone-bottom-tab${id === active ? ' active' : ''}`}
          onClick={() => onSelect && onSelect(id)}
        >
          <span className="pbt-icon">
            <Icon size={22} />
            <CountBadge count={count} />
          </span>
          <span className="pbt-label">{label}</span>
        </button>
      ))}
    </nav>
  );
}

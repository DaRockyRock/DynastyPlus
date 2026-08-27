import Button from '../ui/Button.jsx';
import CountBadge from '../ui/CountBadge.jsx';
import { PhoneIcon } from '../ui/icons.jsx';

// The top-bar phone action with an unread-text count badge. People text the
// coach first week to week, so the badge surfaces how many unread texts are
// waiting in the Messages app.
export default function PhoneButton({ count = 0, onClick }) {
  return (
    <span className="phone-btn-wrap">
      <Button variant="accent" icon={<PhoneIcon />} onClick={onClick}>Phone</Button>
      <CountBadge count={count} />
    </span>
  );
}

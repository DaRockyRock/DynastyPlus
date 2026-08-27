import { useContext } from 'react';
import { AppContext } from '../../context/AppContext.jsx';
import { MessageIcon } from '../ui/icons.jsx';

// Wraps any person's name and reveals a small "text" affordance on hover, so the
// coach can start a conversation with anyone in the app (a recruit, an opposing
// coach, a reporter, a committee member). The `kind` hint tells the backend which
// kind of person this is so it can resolve the right record and frame the chat.
//
// It reads textPerson straight from AppContext (degrading to a no-op outside a
// provider, e.g. in Storybook) and an `onText` prop can override it for stories.
// Clicking the icon never bubbles to a surrounding clickable card; clicking the
// name itself behaves as before.
export default function PersonName({ name, kind, role, team, className = '', children, onText }) {
  const ctx = useContext(AppContext);
  if (!name) return children || null;
  const textPerson = onText || (ctx && ctx.textPerson);

  const open = (e) => {
    e.stopPropagation();
    e.preventDefault();
    if (textPerson) textPerson({ name, kind, role, team });
  };

  return (
    <span className={`person-name${className ? ` ${className}` : ''}`}>
      {children || name}
      <button
        type="button"
        className="person-text-btn"
        onMouseDown={(e) => e.stopPropagation()}
        onClick={open}
        title={`Text ${name}`}
        aria-label={`Text ${name}`}
      >
        <MessageIcon size={12} />
      </button>
    </span>
  );
}

import { AlertIcon, CheckIcon, BoltIcon } from './icons.jsx';

// A small inline note box. `tone` sets the accent and default icon:
//   info (default) | warn | success
const TONE_ICON = { info: BoltIcon, warn: AlertIcon, success: CheckIcon };

export default function Callout({ tone = 'info', icon, title, children }) {
  const Ico = icon || TONE_ICON[tone] || BoltIcon;
  return (
    <div className={`callout callout-${tone}`}>
      <span className="callout-ico"><Ico size={17} /></span>
      <div className="callout-body">
        {title && <span className="callout-title">{title}</span>}
        {children && <span className="callout-text">{children}</span>}
      </div>
    </div>
  );
}

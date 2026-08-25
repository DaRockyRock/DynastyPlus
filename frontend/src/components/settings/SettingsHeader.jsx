import Button from '../ui/Button.jsx';
import { GearIcon, ChevronLeft } from '../ui/icons.jsx';

// Top bar of the Customize studio: brand mark, title, and the exit control.
export default function SettingsHeader({ onClose, children }) {
  return (
    <header className="set-header">
      <span className="set-mark"><GearIcon /></span>
      <div className="set-titles">
        <h1>Customize</h1>
        <span className="sub">Make this dynasty universe your own - names, faces, and identity</span>
      </div>
      <span className="spacer" />
      {children}
      <Button variant="accent" icon={<ChevronLeft />} onClick={onClose}>Back to App</Button>
    </header>
  );
}

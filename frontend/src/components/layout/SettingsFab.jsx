import { GearIcon } from '../ui/icons.jsx';

// Always-on-screen entry point into the Customize studio. Floats in the bottom-
// left corner; clicking opens the full-screen settings flow.
export default function SettingsFab({ onClick }) {
  return (
    <button className="settings-fab" onClick={onClick} aria-label="Customize" title="Customize">
      <GearIcon />
      <span className="fab-tip">Customize</span>
    </button>
  );
}

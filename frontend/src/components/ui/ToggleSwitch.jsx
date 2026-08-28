// Boolean toggle in the game's UI language (cream thumb when on). The whole
// control is one button so the label is clickable too.
export default function ToggleSwitch({ checked = false, onChange, label = '' }) {
  return (
    <button
      type="button"
      className={`toggle${checked ? ' on' : ''}`}
      role="switch"
      aria-checked={checked}
      onClick={() => onChange?.(!checked)}
    >
      <span className="toggle-track"><span className="toggle-thumb" /></span>
      {label ? <span className="toggle-label">{label}</span> : null}
    </button>
  );
}

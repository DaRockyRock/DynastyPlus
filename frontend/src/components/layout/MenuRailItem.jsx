// One button on the game's left menu rail. Cream = selected. `check` renders
// the game's checkbox square (true = checked green, false = empty) like the
// weekly Actions list; `icon` takes an inline SVG or an /game-assets img src
// string; `right` is a free slot (badge, count).
const CHECK_ON = '/game-assets/ui/icons/checkboxchecked.png';
const CHECK_OFF = '/game-assets/ui/icons/checkboxempty.png';

export default function MenuRailItem({
  label, sub, icon = null, check, right = null, active = false, onClick, disabled = false,
}) {
  return (
    <button
      className={`menu-rail-item${active ? ' active' : ''}`}
      onClick={onClick}
      disabled={disabled}
    >
      {icon && (
        <span className="mr-ico">
          {typeof icon === 'string' ? <img src={icon} alt="" /> : icon}
        </span>
      )}
      <span className="mr-label">
        {label}
        {sub && <span className="mr-sub">{sub}</span>}
      </span>
      <span className="mr-right">
        {right}
        {check !== undefined && (
          <img className="mr-check" src={check ? CHECK_ON : CHECK_OFF} alt={check ? 'done' : 'open'} />
        )}
      </span>
    </button>
  );
}

import { CheckIcon } from '../ui/icons.jsx';

// A large selectable card for choosing a connection type. Presentational:
// `selected` + `onSelect` are driven by the parent picker.
//
//   icon     - an icon component (from ui/icons)
//   title    - heading
//   tagline  - one-line summary
//   bullets  - optional list of short feature lines
//   badge    - optional small tag (e.g. "Recommended")
export default function ProviderCard({ icon: Icon, title, tagline, bullets = [], badge, selected = false, onSelect }) {
  return (
    <button
      type="button"
      className={`provider-card${selected ? ' selected' : ''}`}
      aria-pressed={selected}
      onClick={onSelect}
    >
      <span className="pc-check">{selected && <CheckIcon size={14} />}</span>
      <span className="pc-ico">{Icon && <Icon size={26} />}</span>
      <span className="pc-head">
        <span className="pc-title">{title}</span>
        {badge && <span className="pc-badge">{badge}</span>}
      </span>
      {tagline && <span className="pc-tagline">{tagline}</span>}
      {bullets.length > 0 && (
        <ul className="pc-bullets">
          {bullets.map((b) => <li key={b}>{b}</li>)}
        </ul>
      )}
    </button>
  );
}

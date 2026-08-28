// A row of the game's own classic conference marks (from its history tab) for
// the conferences the game ships them for. Clicking one sets it as the
// conference's logo; clicking the selected one again reverts to stock.
// Presentational: `logos` is [{id, url, label}], `value` is the current logo
// URL, selection arrives as `onSelect(url)` ('' means revert to stock).
export default function ConferenceLogoPicker({ logos, value, onSelect }) {
  if (!logos?.length) return null;
  return (
    <div className="cs-histlogos">
      <span className="cs-histlogos-label">Classic logos</span>
      <div className="cs-histlogos-grid">
        {logos.map((l) => {
          const active = value === l.url;
          return (
            <button
              key={l.id}
              type="button"
              className={`cs-histlogo${active ? ' active' : ''}`}
              onClick={() => onSelect?.(active ? '' : l.url)}
              title={l.label}
            >
              <span className="cs-histlogo-mark">
                <img src={l.url} alt={l.label} loading="lazy" />
              </span>
              <span className="cs-histlogo-label">{l.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

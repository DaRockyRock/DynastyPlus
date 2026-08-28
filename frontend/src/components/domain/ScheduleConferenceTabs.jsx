import ConferenceLogo from '../ui/ConferenceLogo.jsx';

// The schedule studio's conference switcher: one cream-selected tab per
// conference (game-extracted mark + name + protected-rivalry tally) plus a
// trailing Non-Conference tab for the league-wide protected rivals, so the
// rules render one conference at a time instead of a wall of stacked cards.
// `conferences` comes from /api/schedule/setup; counts reflect the DRAFT
// rules so the tallies track unsaved edits. Presentational: onChange(key),
// where key is a conference name or NONCON_TAB.
export const NONCON_TAB = '__nonconference__';

export default function ScheduleConferenceTabs({
  conferences = [],
  counts = {},
  nonconCount = 0,
  active,
  onChange,
}) {
  const tab = (key, label, logo, count) => (
    <button
      key={key}
      type="button"
      className={`sr-tab${key === active ? ' active' : ''}`}
      onClick={() => onChange?.(key)}
    >
      {logo}
      <span className="sr-tab-label">{label}</span>
      {count > 0 && <span className="sr-tab-count">{count}</span>}
    </button>
  );
  return (
    <div className="sr-tabs" role="tablist" aria-label="Conference schedule rules">
      {conferences.map((c) => tab(
        c.name,
        c.name,
        <ConferenceLogo name={c.canonical || c.name} size={20} plate={false} />,
        counts[c.name] ?? (c.rivalries || []).length,
      ))}
      {tab(NONCON_TAB, 'Non-Conference', <span className="sr-tab-vs">VS</span>, nonconCount)}
    </div>
  );
}

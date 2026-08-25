import SettingsIcon from './SettingsIcon.jsx';

// Grouped section navigation for the Customize studio. Groups are derived from
// the schema order. Each item shows its icon, label, an item count (for list
// sections) and a dot when the section has unsaved or stored edits.
export default function SettingsNav({ schema, active, onSelect, counts = {}, modified }) {
  const groups = [];
  const byTitle = {};
  schema.forEach((s) => {
    if (!byTitle[s.group]) {
      byTitle[s.group] = { title: s.group, items: [] };
      groups.push(byTitle[s.group]);
    }
    byTitle[s.group].items.push(s);
  });
  const isModified = (key) => (modified instanceof Set ? modified.has(key) : (modified || []).includes(key));

  return (
    <nav className="set-nav">
      {groups.map((g) => (
        <div className="set-nav-group" key={g.title}>
          <div className="grp">{g.title}</div>
          {g.items.map((s) => (
            <button
              key={s.key}
              className={`set-nav-item${s.key === active ? ' active' : ''}`}
              onClick={() => onSelect(s.key)}
            >
              <span className="ico"><SettingsIcon name={s.icon} /></span>
              <span className="lbl">{s.label}</span>
              {counts[s.key] != null && <span className="count">{counts[s.key]}</span>}
              {isModified(s.key) && <span className="dot" title="Edited" />}
            </button>
          ))}
        </div>
      ))}
    </nav>
  );
}

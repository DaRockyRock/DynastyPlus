// Horizontal tab navigation. `tabs` = [{ id, label }].
export default function NavTabs({ tabs, active, onSelect }) {
  return (
    <nav className="tabs">
      {tabs.map((t) => (
        <button
          key={t.id}
          className={`tab${t.id === active ? ' active' : ''}`}
          onClick={() => onSelect(t.id)}
        >
          {t.label}
        </button>
      ))}
    </nav>
  );
}

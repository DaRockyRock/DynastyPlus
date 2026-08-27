// Category filter pills for the Messages list (Staff / Players / Recruits /
// Media, plus an implicit "All"). iOS-style segmented pills.
export default function PhoneTabs({ tabs, active, onSelect }) {
  return (
    <div className="phone-tabs">
      {tabs.map((t) => (
        <button
          key={t}
          className={`phone-tab${t === active ? ' active' : ''}`}
          onClick={() => onSelect(t)}
        >
          {t}
        </button>
      ))}
    </div>
  );
}

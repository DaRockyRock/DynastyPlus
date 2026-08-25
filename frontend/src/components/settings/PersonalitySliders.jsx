import { useSettingsMeta } from './SettingsContext.jsx';

// Fallback trait set so the editor renders in isolation (Storybook) when no
// backend-provided definitions are present. Mirrors backend/personality.py.
const FALLBACK_TRAITS = [
  { key: 'confidence', label: 'Confidence', low: 'Humble', high: 'Brash' },
  { key: 'competitiveness', label: 'Competitiveness', low: 'Easygoing', high: 'Relentless' },
  { key: 'loyalty', label: 'Loyalty', low: 'Mercenary', high: 'Ride or Die' },
  { key: 'composure', label: 'Composure', low: 'Volatile', high: 'Unflappable' },
  { key: 'charisma', label: 'Charisma', low: 'Reserved', high: 'Magnetic' },
  { key: 'ambition', label: 'Ambition', low: 'Content', high: 'Driven' },
  { key: 'ego', label: 'Ego', low: 'Team-First', high: 'Spotlight' },
];

// Editor for a person's 1-100 personality sliders. Reads the trait definitions
// (labels + pole names) from the settings meta context, falling back to a
// built-in set so it works standalone.
export default function PersonalitySliders({ value = {}, onChange, traitDefs }) {
  const meta = useSettingsMeta();
  const defs = (traitDefs && traitDefs.length ? traitDefs : meta.traitDefs);
  const traits = defs && defs.length ? defs : FALLBACK_TRAITS;

  const set = (key, v) => onChange({ ...value, [key]: Number(v) });

  return (
    <div className="persona-sliders">
      {traits.map((t) => {
        const v = value[t.key] ?? 50;
        return (
          <div className="persona-row" key={t.key}>
            <div className="pr-head">
              <span className="pr-label">{t.label}</span>
              <span className="pr-value">{v}</span>
            </div>
            <input
              className="persona-range"
              type="range"
              min={1}
              max={100}
              value={v}
              onChange={(e) => set(t.key, e.target.value)}
              style={{ '--pct': `${v}%` }}
            />
            <div className="pr-poles">
              <span>{t.low}</span>
              <span>{t.high}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

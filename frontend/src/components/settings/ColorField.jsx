import { hexColor } from '../../lib/format.js';

// Hex color editor: a native swatch picker paired with a text input. Stores the
// bare 6-digit hex (no leading #) to match the team color convention.
export default function ColorField({ value, onChange }) {
  const hex = hexColor(value, '#000000');
  const set = (v) => onChange(String(v || '').replace(/^#/, '').slice(0, 6));
  return (
    <div className="color-field">
      <span className="swatch" style={{ background: hex }}>
        <input type="color" value={hex} onChange={(e) => set(e.target.value)} aria-label="Pick color" />
      </span>
      <input
        className="set-input"
        value={String(value || '').replace(/^#/, '')}
        onChange={(e) => set(e.target.value)}
        placeholder="e41c38"
        maxLength={6}
      />
    </div>
  );
}

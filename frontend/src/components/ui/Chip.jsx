import { accentFor } from '../../lib/categories.js';

// Category label, tinted in its accent color. Pass `accent` to override the
// color derived from `category`; the CSS mixes it into the pill's text,
// background, and ring via --chip-accent.
export default function Chip({ category, accent }) {
  const color = accent || accentFor(category);
  return (
    <span className="chip" style={{ '--chip-accent': color }}>
      <span className="dot" />
      {category}
    </span>
  );
}

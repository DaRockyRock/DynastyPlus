// Neutral-site stadium picker over the GAME's real stadium table
// (GET /api/playoff/stadiums: the save's 183 stadiums with derived names and
// the game's own venue-pool tags). Marquee title-game venues lead, then the
// bowl/neutral circuit, then every campus stadium. Emits the picked stadium
// row ({index, name, city}) so callers can store the save-stable index plus
// display strings. Renders nothing when the list is empty (no real save):
// callers fall back to free-text venue/city inputs.
import Select from '../ui/Select.jsx';

const POOL_ORDER = [
  ['marquee', 'Marquee neutral sites'],
  ['neutral_scheduling', 'Neutral-game circuit'],
  ['bowl_and_neutral', 'Bowl venues'],
];

function label(s) {
  const city = s.city ? ` (${s.city})` : '';
  const home = s.home_of ? ` - ${s.home_of}` : '';
  return `${s.name}${city}${home}`;
}

export function orderStadiums(stadiums) {
  const seen = new Set();
  const groups = [];
  for (const [pool, title] of POOL_ORDER) {
    const rows = stadiums.filter((s) => s.pools?.includes(pool) && !seen.has(s.index));
    rows.forEach((s) => seen.add(s.index));
    if (rows.length) groups.push({ title, rows });
  }
  const rest = stadiums
    .filter((s) => !seen.has(s.index))
    .sort((a, b) => a.name.localeCompare(b.name));
  if (rest.length) groups.push({ title: 'Campus stadiums', rows: rest });
  return groups;
}

export default function StadiumSelect({ stadiums = [], value, onPick, placeholder = 'Pick a stadium' }) {
  if (!stadiums.length) return null;
  const byIndex = new Map(stadiums.map((s) => [String(s.index), s]));
  const groups = orderStadiums(stadiums).map((g) => ({
    label: g.title,
    options: g.rows.map((s) => ({ value: String(s.index), label: label(s) })),
  }));
  return (
    <Select
      options={[{ value: '', label: placeholder }]}
      groups={groups}
      value={value == null ? '' : String(value)}
      onValueChange={(v) => onPick?.(v === '' ? null : byIndex.get(v))}
    />
  );
}

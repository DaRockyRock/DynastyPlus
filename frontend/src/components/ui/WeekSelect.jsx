import Select from './Select.jsx';

// Season-week picker for scheduling rules. Value is a 1-based display week
// (the profile's numbering: Week 14 is rivalry week, Week 15 is the Army-Navy
// week) or null for "any week". Weeks carrying a traditional date get their
// name in the label so rules like "the Third Saturday in October" are one
// pick. `weeks` (from /api/schedule/setup) limits and annotates the options;
// without it the full 15-week season is offered.
const WEEK_NAMES = {
  14: 'Rivalry Week',
  15: 'Army-Navy Week',
};

export default function WeekSelect({ value, onChange, weeks = null, allowAny = true, disabled = false }) {
  const list = weeks?.length ? weeks : Array.from({ length: 15 }, (_, i) => ({ week: i + 1 }));
  const options = [
    ...(allowAny ? [{ value: '', label: 'Any week' }] : []),
    ...list.map((w) => {
      const wk = typeof w === 'number' ? w : w.week;
      const name = WEEK_NAMES[wk];
      const slots = typeof w === 'object' && w.slots != null ? w.slots : null;
      let label = `Week ${wk}`;
      if (name) label += ` (${name})`;
      else if (slots != null && slots <= 12) label += ` (${slots} slot${slots === 1 ? '' : 's'})`;
      return { value: String(wk), label };
    }),
  ];
  return (
    <Select
      options={options}
      value={value == null ? '' : String(value)}
      onValueChange={(v) => onChange?.(v === '' ? null : Number(v))}
      disabled={disabled}
    />
  );
}

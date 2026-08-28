// Native select styled to the design system (.set-select, which draws its own
// arrow). `options` is a list of { value, label }; `groups` (optional) is a
// list of { label, options } rendered as optgroups after the flat options.
export default function Select({ options = [], groups = [], value, onValueChange, onChange, ...rest }) {
  return (
    <select
      className="set-select"
      value={value ?? ''}
      onChange={(e) => { onValueChange?.(e.target.value); onChange?.(e); }}
      {...rest}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
      {groups.map((g) => (
        <optgroup key={g.label} label={g.label}>
          {g.options.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}

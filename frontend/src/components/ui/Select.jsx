// Native select styled to the design system (.set-select, which draws its own
// arrow). `options` is a list of { value, label }.
export default function Select({ options = [], value, onValueChange, onChange, ...rest }) {
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
    </select>
  );
}

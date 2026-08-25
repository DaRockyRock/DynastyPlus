// Plain text input styled to the design system (.set-input). A thin component so
// pages never hand-roll a raw <input>. Forwards any extra props (type, value,
// placeholder, onChange, etc.) straight through.
export default function TextInput({ className = '', onValueChange, onChange, ...rest }) {
  return (
    <input
      className={['set-input', className].filter(Boolean).join(' ')}
      onChange={(e) => { onValueChange?.(e.target.value); onChange?.(e); }}
      {...rest}
    />
  );
}

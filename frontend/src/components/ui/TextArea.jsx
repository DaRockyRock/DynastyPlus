// Multi-line text input styled to the design system (.set-textarea). A thin
// component so pages never hand-roll a raw <textarea>. Forwards any extra
// props (value, placeholder, rows, maxLength, onChange, etc.) straight through.
export default function TextArea({ className = '', onValueChange, onChange, ...rest }) {
  return (
    <textarea
      className={['set-textarea', className].filter(Boolean).join(' ')}
      onChange={(e) => { onValueChange?.(e.target.value); onChange?.(e); }}
      {...rest}
    />
  );
}

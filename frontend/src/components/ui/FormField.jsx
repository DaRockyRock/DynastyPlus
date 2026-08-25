// A labeled form control wrapper. Mirrors the Customize studio field styling
// (.set-field / .set-label / .set-help) so any one-off form in the app gets the
// same look without going through the schema-driven SettingsField.
//
//   label  - field label (capped display type)
//   help   - optional helper line under the control
//   width  - 'full' | 'half' | 'third' | 'quarter' (grid span inside a .set-grid)
//   htmlFor / id wiring is left to the caller's control via children.
export default function FormField({ label, help, width = 'full', className = '', children }) {
  const cls = ['set-field', `w-${width}`, className].filter(Boolean).join(' ');
  return (
    <label className={cls}>
      {label && <span className="set-label">{label}</span>}
      {children}
      {help && <span className="set-help">{help}</span>}
    </label>
  );
}

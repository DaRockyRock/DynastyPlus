// Pill badge. Optional `label` (muted key) + `value` (emphasized), or children.
// variant: 'week' | 'rank-cfp' | 'rank-ap' | undefined
export default function Badge({ variant, label, value, children, className = '' }) {
  const cls = ['badge', variant, className].filter(Boolean).join(' ');
  return (
    <span className={cls}>
      {label != null && <span className="k">{label}</span>}
      {value != null && <span className="v">{value}</span>}
      {children}
    </span>
  );
}

// Base button. Variants map to the design-system button styles.
//   action - bordered surface button with optional icon + label (default)
//   accent - filled team-color button
//   compact - compact bordered button
const VARIANT_CLASS = {
  action: 'icon-btn',
  accent: 'icon-btn accent',
  compact: 'icon-btn compact',
};

export default function Button({
  variant = 'action',
  icon = null,
  spinning = false,
  children,
  className = '',
  ...rest
}) {
  const cls = [VARIANT_CLASS[variant] || 'icon-btn', spinning ? 'spinning' : '', className]
    .filter(Boolean)
    .join(' ');
  return (
    <button className={cls} {...rest}>
      {icon}
      {children}
    </button>
  );
}

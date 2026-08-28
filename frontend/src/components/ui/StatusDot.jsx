// A small colored status indicator. `tone` maps to a broadcast accent:
//   live (green) | idle/amber | off (muted) | error (red)
// `pulse` adds a soft pulsing glow for the live state.
export default function StatusDot({ tone = 'off', pulse = false, size = 8 }) {
  const cls = ['status-dot', `dot-${tone}`, pulse ? 'dot-pulse' : ''].filter(Boolean).join(' ');
  return <span className={cls} style={{ width: size, height: size }} aria-hidden="true" />;
}

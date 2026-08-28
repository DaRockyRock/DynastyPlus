// Legibility backing for a logo on the dark field. Real team/conference marks
// often include near-black elements (e.g. the Ohio State block O) that vanish
// against the deep broadcast background. LogoPlate sits behind the mark as a
// light "broadcast chip" - the same convention real score-bug graphics use - so
// every logo reads regardless of its own colors. Wraps any logo image; the mark
// is padded inside the plate.
export default function LogoPlate({ size = 40, radius, className = '', title, style, children }) {
  return (
    <span
      className={`logo-plate ${className}`.trim()}
      style={{ width: size, height: size, ...(radius != null ? { borderRadius: radius } : null), ...style }}
      title={title}
    >
      {children}
    </span>
  );
}

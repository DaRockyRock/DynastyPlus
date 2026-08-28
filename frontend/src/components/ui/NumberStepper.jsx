// Numeric stepper in the game's UI language: minus / value / plus. Clamps to
// [min, max]. Direct typing is allowed; invalid input is ignored.
export default function NumberStepper({ value, onChange, min = 0, max = 999, step = 1, suffix = '' }) {
  const clamp = (v) => Math.max(min, Math.min(max, v));
  const set = (v) => onChange?.(clamp(v));
  const current = Number.isFinite(value) ? value : min;
  return (
    <span className="num-stepper">
      <button type="button" className="num-btn" onClick={() => set(current - step)} disabled={current <= min} aria-label="decrease">&minus;</button>
      <input
        className="num-value"
        type="number"
        min={min}
        max={max}
        value={current}
        onChange={(e) => {
          const v = parseInt(e.target.value, 10);
          if (!Number.isNaN(v)) set(v);
        }}
      />
      {suffix ? <span className="num-suffix">{suffix}</span> : null}
      <button type="button" className="num-btn" onClick={() => set(current + step)} disabled={current >= max} aria-label="increase">+</button>
    </span>
  );
}

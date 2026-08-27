// A single label/value row used inside panels and tiles. `k` and `v` accept
// nodes so callers can embed badges, bars, etc.
export default function KeyValue({ k, v }) {
  return (
    <div className="kv">
      <span className="k">{k}</span>
      <span className="v">{v}</span>
    </div>
  );
}

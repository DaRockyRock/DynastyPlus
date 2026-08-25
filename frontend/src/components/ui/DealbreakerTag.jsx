// What a recruit or player weighs most (e.g. "Brand Exposure"). A small
// outlined "file stamp" tag so it sits quietly next to names.
export default function DealbreakerTag({ value }) {
  if (!value) return null;
  return <span className="dealbreaker-tag" title="Dealbreaker">{value}</span>;
}
